import logging
import random
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.evolution_engine import RosterConstraints
from src.player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer
from src.sb_template import POSITION_GROUPS, _POS_TO_GROUP, SuperBowlTemplateAnalyzer

logger = logging.getLogger(__name__)

_N_MONTE_CARLO = 1000


class PortfolioOptimizer:
    """Portfolio theory analysis for NFL roster construction.

    Mirrors EvolutionEngine's two-list + constraints constructor pattern.
    Values all inputs at init so downstream methods work on valued assets.
    """

    def __init__(
        self,
        current_roster: List[PlayerAsset],
        available_players: Optional[List[PlayerAsset]] = None,
        constraints: Optional[RosterConstraints] = None,
    ) -> None:
        """Initialise and value all input players.

        Args:
            current_roster: The team's current roster.
            available_players: Additional players for Monte Carlo simulations.
                Defaults to [] if None.
            constraints: Roster rules. Defaults to RosterConstraints().
        """
        self._constraints = constraints if constraints is not None else RosterConstraints()
        self._available_players: List[PlayerAsset] = (
            [] if available_players is None else list(available_players)
        )
        model = PlayerValuationModel()
        self._current_roster = model.value_roster(list(current_roster))
        if self._available_players:
            self._available_players = model.value_roster(self._available_players)

    def _is_valid_roster(self, roster: List[PlayerAsset]) -> bool:
        if not (self._constraints.min_roster_size
                <= len(roster)
                <= self._constraints.max_roster_size):
            return False
        if sum(p.cap_hit_2026 for p in roster) > self._constraints.salary_cap:
            return False
        pos_counts: Dict[str, int] = {}
        for p in roster:
            pos_counts[p.position] = pos_counts.get(p.position, 0) + 1
        for pos, (min_c, max_c) in self._constraints.position_limits.items():
            count = pos_counts.get(pos, 0)
            if count < min_c or count > max_c:
                return False
        return True

    def _random_roster(self, pool: List[PlayerAsset]) -> Optional[List[PlayerAsset]]:
        """Attempt to build one valid random roster from the pool."""
        shuffled = pool.copy()
        random.shuffle(shuffled)
        roster: List[PlayerAsset] = []
        pos_counts: Dict[str, int] = {}
        cap_used = 0.0

        # Phase 1: greedy fill up to max counts
        for player in shuffled:
            pos = player.position
            _, max_c = self._constraints.position_limits.get(pos, (0, 0))
            if (pos_counts.get(pos, 0) < max_c
                    and cap_used + player.cap_hit_2026 <= self._constraints.salary_cap
                    and len(roster) < self._constraints.max_roster_size):
                roster.append(player)
                pos_counts[pos] = pos_counts.get(pos, 0) + 1
                cap_used += player.cap_hit_2026

        # Phase 2: fill any positions that didn't reach their minimum
        for pos, (min_c, _) in self._constraints.position_limits.items():
            while pos_counts.get(pos, 0) < min_c:
                candidates = [
                    p for p in shuffled
                    if p.position == pos and p not in roster
                ]
                if not candidates:
                    break
                cheapest = min(candidates, key=lambda p: p.cap_hit_2026)
                if cap_used + cheapest.cap_hit_2026 <= self._constraints.salary_cap:
                    roster.append(cheapest)
                    pos_counts[pos] = pos_counts.get(pos, 0) + 1
                    cap_used += cheapest.cap_hit_2026
                else:
                    break

        if self._is_valid_roster(roster):
            return roster
        return None

    def _roster_metrics(self, roster: List[PlayerAsset]) -> Dict[str, float]:
        analyzer = PortfolioAnalyzer(roster)
        return {
            "risk": analyzer.portfolio_risk(),
            "efficiency": analyzer.portfolio_efficiency(),
            "return_value": analyzer.total_value(),
            "cap_utilization": analyzer.total_cost() / self._constraints.salary_cap,
        }

    def calculate_efficient_frontier(self, n_points: int = 20) -> pd.DataFrame:
        """Monte Carlo efficient frontier over current_roster + available_players.

        Generates up to 1000 random valid rosters, then extracts n_points
        frontier points by binning on risk and taking max-efficiency per bin.

        Args:
            n_points: Number of frontier points to return.

        Returns:
            DataFrame with columns: risk, efficiency, return_value, cap_utilization.
        """
        pool = self._current_roster + self._available_players
        samples: List[Dict[str, float]] = []

        for _ in range(_N_MONTE_CARLO):
            roster = self._random_roster(pool)
            if roster is not None:
                samples.append(self._roster_metrics(roster))

        if not samples:
            logger.warning(
                "Monte Carlo produced 0 valid rosters — check pool size and constraints"
            )
            return pd.DataFrame(
                columns=["risk", "efficiency", "return_value", "cap_utilization"]
            )

        df = pd.DataFrame(samples)
        df["_bin"] = pd.cut(df["risk"], bins=n_points, labels=False)
        frontier = (
            df.sort_values("efficiency", ascending=False)
            .groupby("_bin", observed=True)
            .first()
            .reset_index(drop=True)
            [["risk", "efficiency", "return_value", "cap_utilization"]]
        )
        return frontier.sort_values("risk").reset_index(drop=True)

    def calculate_position_efficient_allocation(self) -> Dict[str, Dict[str, object]]:
        """Compare current position cap allocation to the optimal from top Monte Carlo rosters.

        Runs a single Monte Carlo pass collecting both efficiency and position data.
        Top 10% rosters by efficiency determine the "optimal" allocation.

        Args: None (uses self._current_roster and self._available_players).

        Returns:
            Dict mapping position group → {current_pct, optimal_pct, delta, recommendation}.
        """
        pool = self._current_roster + self._available_players
        samples: List[Dict] = []

        for _ in range(_N_MONTE_CARLO):
            roster = self._random_roster(pool)
            if roster is None:
                continue
            metrics = self._roster_metrics(roster)
            # Record position allocation alongside metrics
            total_cap = sum(p.cap_hit_2026 for p in roster)
            group_cap: Dict[str, float] = {g: 0.0 for g in POSITION_GROUPS}
            if total_cap > 0:
                for p in roster:
                    g = _POS_TO_GROUP.get(p.position.upper().strip())
                    if g:
                        group_cap[g] += p.cap_hit_2026 / total_cap * 100
            samples.append({**metrics, **{f"pos_{g}": v for g, v in group_cap.items()}})

        current_alloc = SuperBowlTemplateAnalyzer().calculate_position_allocation(
            self._current_roster
        )

        if not samples:
            logger.warning(
                "Monte Carlo produced 0 valid rosters — returning current allocation as optimal"
            )
            result: Dict[str, Dict[str, object]] = {}
            for group in POSITION_GROUPS:
                current_pct = current_alloc.get(group, 0.0)
                result[group] = {
                    "current_pct": round(current_pct, 2),
                    "optimal_pct": round(current_pct, 2),
                    "delta": 0.0,
                    "recommendation": "maintain",
                }
            return result

        df = pd.DataFrame(samples)
        threshold = df["efficiency"].quantile(0.90)
        top_df = df[df["efficiency"] >= threshold]

        if top_df.empty:
            top_df = df  # fallback: use all samples

        result = {}
        for group in POSITION_GROUPS:
            col = f"pos_{group}"
            current_pct = current_alloc.get(group, 0.0)
            optimal_pct = float(top_df[col].mean()) if col in top_df.columns else current_pct
            delta = optimal_pct - current_pct
            if abs(delta) <= 2.0:
                recommendation = "maintain"
            elif delta > 0:
                recommendation = "increase"
            else:
                recommendation = "decrease"
            result[group] = {
                "current_pct": round(current_pct, 2),
                "optimal_pct": round(optimal_pct, 2),
                "delta": round(delta, 2),
                "recommendation": recommendation,
            }
        return result

    def identify_pareto_optimal_players(
        self, available: List[PlayerAsset]
    ) -> List[PlayerAsset]:
        """Return players on the Pareto frontier of expected_value vs cap_hit_2026.

        A player is dominated if another player has both strictly higher
        expected_value AND strictly lower cap_hit_2026.

        Args:
            available: Pool of PlayerAsset objects to evaluate.

        Returns:
            List of non-dominated PlayerAsset objects.
        """
        pareto: List[PlayerAsset] = []
        for candidate in available:
            dominated = any(
                other.expected_value > candidate.expected_value
                and other.cap_hit_2026 < candidate.cap_hit_2026
                for other in available
                if other is not candidate
            )
            if not dominated:
                pareto.append(candidate)
        return pareto

    def calculate_marginal_value(
        self,
        current_roster: List[PlayerAsset],
        candidate: PlayerAsset,
    ) -> float:
        """Return the efficiency delta from swapping candidate into the roster.

        Replaces the lowest-expected_value player at the same position.
        Returns 0.0 if no same-position player exists.

        Args:
            current_roster: Current roster as valued PlayerAsset objects.
            candidate: The player to evaluate.

        Returns:
            Delta in portfolio_efficiency (positive = improvement).
        """
        same_pos = [p for p in current_roster if p.position == candidate.position]
        if not same_pos:
            return 0.0

        weakest = min(same_pos, key=lambda p: p.expected_value)
        new_roster = [p for p in current_roster if p is not weakest] + [candidate]

        before = PortfolioAnalyzer(current_roster).portfolio_efficiency()
        after = PortfolioAnalyzer(new_roster).portfolio_efficiency()
        return round(after - before, 6)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    from src.player_valuation import PlayerValuationModel
    from src.evolution_engine import RosterConstraints

    demo = [
        PlayerAsset("den_qb_d", "Demo QB", "QB", "DEN", 27,
                    37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("den_wr_d", "Demo WR", "WR", "DEN", 25,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
    ]
    c = RosterConstraints()
    c.min_roster_size = 2
    c.max_roster_size = 3
    c.salary_cap = 200_000_000
    c.position_limits = {"QB": (1, 2), "WR": (1, 2)}

    opt = PortfolioOptimizer(current_roster=demo, constraints=c)
    pareto = opt.identify_pareto_optimal_players(opt._current_roster)
    logger.info("Pareto optimal players: %s", [p.name for p in pareto])

    candidate = PlayerValuationModel().value_roster([
        PlayerAsset("den_qb_new", "Better QB", "QB", "DEN", 24,
                    20_000_000, 3, 10_000_000, 80_000_000, 60.0, 1050, 0)
    ])[0]
    mv = opt.calculate_marginal_value(opt._current_roster, candidate)
    logger.info("Marginal value of Better QB: %+.4f", mv)
