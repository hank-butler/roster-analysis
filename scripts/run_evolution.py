"""Pre-compute evolution results for the dashboard demo.

Runs the EvolutionEngine on AFC West players where we have position data
(QB, WR, RB, TE, DL, LB, K, P, LS) and saves results to
data/processed/evolution_results.json.

Run from project root:
    conda run -n nfl_analytics python scripts/run_evolution.py
"""
import json
import logging
import sys
from dataclasses import field
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evolution_engine import EvolutionEngine, RosterConstraints, Chromosome
from src.player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

VALID_POSITIONS = {"QB", "WR", "RB", "TE", "DL", "LB", "K", "LS"}
# Note: P (punter) excluded — DEN's 2026 punter is not captured in the OTC data pipeline yet.
OUTPUT_PATH = Path("data/processed/evolution_results.json")


def load_players() -> list:
    df = pd.read_csv("data/processed/player_assets_ready.csv")
    players = []
    for _, r in df.iterrows():
        if str(r["position"]) not in VALID_POSITIONS:
            continue
        players.append(PlayerAsset(
            player_id=str(r["player_id"]),
            name=str(r["name"]),
            position=str(r["position"]),
            team=str(r["team"]),
            age=int(r["age"]),
            cap_hit_2026=float(r["cap_hit_2026"]),
            years_remaining=int(r["years_remaining"]),
            guaranteed_money=float(r["guaranteed_money"]),
            total_contract_value=float(r["total_contract_value"]),
            epa_total=float(r["epa_total"]),
            snaps_played=int(r["snaps_played"]),
            games_missed=int(r["games_missed"]),
        ))
    return PlayerValuationModel().value_roster(players)


def make_constraints() -> RosterConstraints:
    """Constraints scoped to the positions we have data for."""
    c = RosterConstraints()
    c.min_roster_size = 25
    c.max_roster_size = 45
    c.salary_cap = 165_000_000   # portion of cap covering these position groups
    c.position_limits = {
        "QB":  (2, 4),
        "RB":  (3, 6),
        "WR":  (5, 9),
        "TE":  (2, 5),
        "DL":  (4, 9),
        "LB":  (4, 9),
        "K":   (1, 1),
        "LS":  (1, 2),
    }
    return c


def player_to_dict(p: PlayerAsset) -> dict:
    return {
        "name": p.name,
        "position": p.position,
        "team": p.team,
        "age": p.age,
        "cap_hit": p.cap_hit_2026,
        "expected_value": round(p.expected_value, 2),
        "efficiency_ratio": round(p.efficiency_ratio, 4),
        "risk_score": round(p.risk_score, 4),
        "fair_value": round(p.fair_value, 2),
    }


def main():
    logger.info("Loading players...")
    all_players = load_players()
    den_players = [p for p in all_players if p.team == "DEN"]
    logger.info(f"DEN known-position players: {len(den_players)}")
    logger.info(f"Total AFC West pool: {len(all_players)}")

    constraints = make_constraints()

    # Score the current DEN roster via portfolio metrics (not fitness fn,
    # which penalises position-count mismatches in the raw data)
    pa_current_pre = PortfolioAnalyzer(den_players)
    current_efficiency = pa_current_pre.portfolio_efficiency()
    current_risk = pa_current_pre.portfolio_risk()
    logger.info(f"Current DEN portfolio efficiency: {current_efficiency:.4f}, risk: {current_risk:.4f}")

    # Run the evolution
    engine = EvolutionEngine(
        current_roster=den_players,
        available_players=den_players,   # optimize within DEN's own roster
        constraints=constraints,
        valuation_model=PlayerValuationModel(),
    )
    engine.population_size = 60
    engine.generations = 40
    engine.mutation_rate = 0.15
    engine.crossover_rate = 0.80
    engine.elitism_count = 5

    best_chromosome, history = engine.evolve()
    best_fitness = engine.best_fitness_ever
    logger.info(f"Best evolved fitness: {best_fitness:.4f}")

    # Build before/after diff
    current_ids = {p.player_id for p in den_players}
    evolved_ids = {p.player_id for p in best_chromosome.players}
    removed = [p for p in den_players if p.player_id not in evolved_ids]
    added = [p for p in best_chromosome.players if p.player_id not in current_ids]
    kept = [p for p in best_chromosome.players if p.player_id in current_ids]

    pa_evolved = PortfolioAnalyzer(best_chromosome.players)
    logger.info(
        f"Efficiency: {current_efficiency:.4f} → {pa_evolved.portfolio_efficiency():.4f} "
        f"(+{((pa_evolved.portfolio_efficiency() / current_efficiency) - 1) * 100:.1f}%)"
    )

    results = {
        "metadata": {
            "population_size": engine.population_size,
            "generations": engine.generations,
            "salary_cap": constraints.salary_cap,
            "positions_included": sorted(VALID_POSITIONS),
            "note": "Optimizes within DEN's current roster (QB/WR/RB/TE/DL/LB/K/LS). P excluded — punter not in pipeline yet. Cross-team acquisition is future work."
        },
        "current_roster": {
            "players": [player_to_dict(p) for p in sorted(den_players, key=lambda p: -p.cap_hit_2026)],
            "cap_used": round(sum(p.cap_hit_2026 for p in den_players)),
            "portfolio_efficiency": round(pa_current_pre.portfolio_efficiency(), 4),
            "portfolio_risk": round(pa_current_pre.portfolio_risk(), 4),
        },
        "evolved_roster": {
            "fitness": round(best_fitness, 4),
            "players": [player_to_dict(p) for p in sorted(best_chromosome.players, key=lambda p: -p.cap_hit_2026)],
            "cap_used": round(sum(p.cap_hit_2026 for p in best_chromosome.players)),
            "portfolio_efficiency": round(pa_evolved.portfolio_efficiency(), 4),
            "portfolio_risk": round(pa_evolved.portfolio_risk(), 4),
        },
        "changes": {
            "removed": [player_to_dict(p) for p in sorted(removed, key=lambda p: -p.cap_hit_2026)],
            "added": [player_to_dict(p) for p in sorted(added, key=lambda p: -p.cap_hit_2026)],
            "kept_count": len(kept),
        },
        "history": [
            {
                "generation": h["generation"],
                "best_fitness": h["best_fitness"],
                "avg_fitness": h["avg_fitness"],
                "diversity": h.get("diversity", 0),
            }
            for h in history
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    logger.info(f"Saved results to {OUTPUT_PATH}")
    logger.info(
        f"Additions drawn from DEN's own roster. "
        f"Kept: {len(kept)}, removed: {len(removed)}, added back: {len(added)}"
    )
    logger.info(f"Players removed: {[p['name'] for p in results['changes']['removed']]}")
    logger.info(f"Players added:   {[p['name'] for p in results['changes']['added']]}")


if __name__ == "__main__":
    main()
