# Analysis Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build four pure-Python analysis modules — SuperBowl template matching, portfolio optimization, Plotly visualizations, and division comparison — that sit between the data pipeline and the Streamlit/AI layer.

**Architecture:** Implemented in dependency order: `sb_template.py` (stateless, no deps) → `portfolio_optimizer.py` (depends only on `player_valuation.py`) → `visualizations.py` (depends on both) → `nfc_west_comparison.py` (coordination layer over all three). `POSITION_GROUPS` is defined once in `sb_template.py` and imported everywhere else.

**Tech Stack:** Python 3.11, pandas, numpy, plotly, pytest. Conda env: `nfl_analytics`. Run all commands from `/home/hankbutler/Desktop/Projects/roster-analysis`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/sb_template.py` | Create | SB winner template metrics + similarity scoring |
| `src/portfolio_optimizer.py` | Create | Efficient frontier, Pareto analysis, marginal value |
| `src/visualizations.py` | Create | Six standalone Plotly figure functions |
| `src/nfc_west_comparison.py` | Create | Division coordination layer |
| `CLAUDE.md` | Modify | Add `src/nfc_west_comparison.py` to architecture listing |
| `tests/test_sb_template.py` | Create | Unit tests for Task 1 |
| `tests/test_portfolio_optimizer.py` | Create | Unit tests for Task 2 |
| `tests/test_visualizations.py` | Create | Unit tests for Task 3 |
| `tests/test_nfc_west_comparison.py` | Create | Unit tests for Task 4 |

---

## Shared test helper (used in all 4 test files)

Every test file defines this local helper at the top — do not import across test files:

```python
from src.player_valuation import PlayerAsset

def _make_player(
    position: str,
    cap_hit: float,
    age: int,
    name: str = "Test Player",
    team: str = "SF",
    epa: float = 5.0,
    expected_value: float = 0.0,
    risk_score: float = 0.2,
) -> PlayerAsset:
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name,
        position=position,
        team=team,
        age=age,
        cap_hit_2026=cap_hit,
        years_remaining=2,
        guaranteed_money=cap_hit * 0.5,
        total_contract_value=cap_hit * 2,
        epa_total=epa,
        snaps_played=800,
        games_missed=1,
    )
    p.expected_value = expected_value
    p.risk_score = risk_score
    p.fair_value = expected_value * (1 - risk_score)
    p.efficiency_ratio = expected_value / cap_hit if cap_hit > 0 else 0.0
    p.sharpe_ratio = (expected_value - cap_hit) / (risk_score * cap_hit) if risk_score > 0 and cap_hit > 0 else 0.0
    return p
```

---

### Task 1: `src/sb_template.py`

**Files:**
- Create: `src/sb_template.py`
- Create: `tests/test_sb_template.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sb_template.py`:

```python
import pytest
from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer, POSITION_GROUPS


def _make_player(position, cap_hit, age, name="Test", team="SF", epa=5.0,
                 expected_value=0.0, risk_score=0.2):
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=epa, snaps_played=800, games_missed=1,
    )
    p.expected_value = expected_value
    p.risk_score = risk_score
    return p


@pytest.fixture
def simple_roster():
    return [
        _make_player("QB",   30_000_000, 27, "Purdy"),
        _make_player("WR",   20_000_000, 26, "Aiyuk"),
        _make_player("RB",   10_000_000, 25, "CMC"),
        _make_player("OT",   15_000_000, 30, "Williams"),
        _make_player("EDGE", 12_000_000, 28, "Bosa"),
    ]


# ---- POSITION_GROUPS -------------------------------------------------------

def test_position_groups_has_eight_keys():
    assert set(POSITION_GROUPS.keys()) == {
        "QB", "SKILL", "OL", "EDGE", "DL", "LB", "DB", "SPECIAL"
    }


# ---- calculate_position_allocation -----------------------------------------

def test_position_allocation_sums_to_100(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation(simple_roster)
    total = sum(result.values())
    assert abs(total - 100.0) < 0.01


def test_position_allocation_empty_roster():
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation([])
    assert all(v == 0.0 for v in result.values())


def test_position_allocation_groups_skill_positions(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation(simple_roster)
    total_cap = 30 + 20 + 10 + 15 + 12  # millions
    expected_skill = (20 + 10) / total_cap * 100  # WR + RB
    assert abs(result["SKILL"] - expected_skill) < 0.01


def test_position_allocation_skips_blank_position():
    analyzer = SuperBowlTemplateAnalyzer()
    blank = _make_player("", 10_000_000, 25, "Unknown")
    known = _make_player("QB", 30_000_000, 27, "Purdy")
    result = analyzer.calculate_position_allocation([blank, known])
    # Only QB cap counts; blank is skipped
    assert result["QB"] == 100.0


# ---- calculate_age_distribution --------------------------------------------

def test_age_distribution_sums_to_100(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_age_distribution(simple_roster)
    assert abs(sum(result.values()) - 100.0) < 0.01


def test_age_distribution_correct_buckets():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [
        _make_player("QB", 10_000_000, 23),  # 22-25
        _make_player("WR", 10_000_000, 24),  # 22-25
        _make_player("RB", 10_000_000, 27),  # 26-29
        _make_player("OT", 10_000_000, 32),  # 30+
    ]
    result = analyzer.calculate_age_distribution(roster)
    assert abs(result["22-25"] - 50.0) < 0.01
    assert abs(result["26-29"] - 25.0) < 0.01
    assert abs(result["30+"]   - 25.0) < 0.01


def test_age_distribution_excludes_age_zero():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [
        _make_player("QB", 10_000_000, 0),   # excluded
        _make_player("WR", 10_000_000, 25),  # 22-25
    ]
    result = analyzer.calculate_age_distribution(roster)
    assert abs(result["22-25"] - 100.0) < 0.01


# ---- calculate_star_concentration ------------------------------------------

def test_star_concentration_top5_leq_top10():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", float(i) * 1_000_000, 25) for i in range(1, 16)]
    result = analyzer.calculate_star_concentration(roster)
    assert result["top_5"] <= result["top_10"]


def test_star_concentration_correct_values():
    analyzer = SuperBowlTemplateAnalyzer()
    # 10 players: cap hits 1M–10M
    roster = [_make_player("QB", float(i) * 1_000_000, 25, f"P{i}") for i in range(1, 11)]
    result = analyzer.calculate_star_concentration(roster)
    total = sum(range(1, 11)) * 1_000_000  # 55M
    top5 = sum(range(6, 11)) * 1_000_000  # 40M (players 6–10 are highest)
    assert abs(result["top_5"] - top5 / total * 100) < 0.01


# ---- build_sb_template -----------------------------------------------------

def test_build_sb_template_keys():
    analyzer = SuperBowlTemplateAnalyzer()
    template = analyzer.build_sb_template()
    assert set(template.keys()) == {"position_allocation", "age_distribution", "star_concentration"}
    assert set(template["position_allocation"].keys()) == {
        "QB", "SKILL", "OL", "EDGE", "DL", "LB", "DB", "SPECIAL"
    }
    assert set(template["age_distribution"].keys()) == {"22-25", "26-29", "30+"}
    assert set(template["star_concentration"].keys()) == {"top_5", "top_10"}


def test_build_sb_template_position_sums_to_100():
    analyzer = SuperBowlTemplateAnalyzer()
    template = analyzer.build_sb_template()
    assert abs(sum(template["position_allocation"].values()) - 100.0) < 0.01


# ---- calculate_similarity_score --------------------------------------------

def test_similarity_score_keys():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    assert set(result.keys()) == {
        "position_similarity", "age_similarity", "concentration_similarity",
        "overall_similarity", "gaps",
    }


def test_similarity_score_range():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    for key in ("position_similarity", "age_similarity", "concentration_similarity", "overall_similarity"):
        assert 0.0 <= result[key] <= 100.0


def test_similarity_score_gaps_is_list_of_strings():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    assert isinstance(result["gaps"], list)
    assert all(isinstance(g, str) for g in result["gaps"])


def test_similarity_overall_weighted_correctly():
    analyzer = SuperBowlTemplateAnalyzer()
    # Use a roster that matches the SB template exactly
    template = analyzer.build_sb_template()
    # Build a fake roster where position/age/concentration match template
    # Then overall_similarity should be ~100
    # We'll just check the weighting formula holds approximately
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    expected = (
        0.50 * result["position_similarity"] +
        0.30 * result["age_similarity"] +
        0.20 * result["concentration_similarity"]
    )
    assert abs(result["overall_similarity"] - expected) < 0.01
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
conda run -n nfl_analytics pytest tests/test_sb_template.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'src.sb_template'`

- [ ] **Step 3: Implement `src/sb_template.py`**

```python
import logging
from typing import Dict, List

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

POSITION_GROUPS: Dict[str, List[str]] = {
    "QB":      ["QB"],
    "SKILL":   ["WR", "RB", "TE"],
    "OL":      ["OT", "OG", "C"],
    "EDGE":    ["EDGE"],
    "DL":      ["DL"],
    "LB":      ["LB"],
    "DB":      ["CB", "S"],
    "SPECIAL": ["K", "P", "LS"],
}

# Reverse map: individual position → group name
_POS_TO_GROUP: Dict[str, str] = {
    pos: group
    for group, positions in POSITION_GROUPS.items()
    for pos in positions
}

_AGE_BUCKETS = ["22-25", "26-29", "30+"]

_SB_TEMPLATE = {
    "position_allocation": {
        "QB": 15.0, "SKILL": 25.0, "OL": 15.0, "EDGE": 12.0,
        "DL": 10.0, "LB": 8.0, "DB": 12.0, "SPECIAL": 3.0,
    },
    "age_distribution": {
        "22-25": 38.0, "26-29": 42.0, "30+": 20.0,
    },
    "star_concentration": {
        "top_5": 34.0, "top_10": 54.0,
    },
}


class SuperBowlTemplateAnalyzer:
    """Compares a roster's structure against a Super Bowl winner template."""

    def calculate_position_allocation(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of total cap allocated to each position group.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict mapping position group name to cap percentage (0–100).
        """
        totals: Dict[str, float] = {g: 0.0 for g in POSITION_GROUPS}
        total_cap = 0.0

        for player in roster:
            group = _POS_TO_GROUP.get(player.position.upper().strip())
            if group is None:
                logger.warning(
                    f"Unrecognized position '{player.position}' for {player.name} — skipped"
                )
                continue
            totals[group] += player.cap_hit_2026
            total_cap += player.cap_hit_2026

        if total_cap == 0:
            return {g: 0.0 for g in POSITION_GROUPS}

        return {g: round(v / total_cap * 100, 4) for g, v in totals.items()}

    def calculate_age_distribution(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of roster in each age bucket (22-25, 26-29, 30+).

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict mapping bucket label to percentage of roster count (0–100).
        """
        counts = {"22-25": 0, "26-29": 0, "30+": 0}
        valid = 0

        for player in roster:
            if player.age == 0:
                logger.warning(f"Age 0 for {player.name} — excluded from age distribution")
                continue
            valid += 1
            if player.age <= 25:
                counts["22-25"] += 1
            elif player.age <= 29:
                counts["26-29"] += 1
            else:
                counts["30+"] += 1

        if valid == 0:
            return {b: 0.0 for b in _AGE_BUCKETS}

        return {b: round(c / valid * 100, 4) for b, c in counts.items()}

    def calculate_star_concentration(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of cap held by top 5 and top 10 players by cap hit.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict with keys 'top_5' and 'top_10', each a cap percentage (0–100).
        """
        if not roster:
            return {"top_5": 0.0, "top_10": 0.0}

        sorted_caps = sorted(
            (p.cap_hit_2026 for p in roster), reverse=True
        )
        total_cap = sum(sorted_caps)
        if total_cap == 0:
            return {"top_5": 0.0, "top_10": 0.0}

        return {
            "top_5":  round(sum(sorted_caps[:5]) / total_cap * 100, 4),
            "top_10": round(sum(sorted_caps[:10]) / total_cap * 100, 4),
        }

    def build_sb_template(self) -> Dict:
        """Return hardcoded SB winner averages (2020–2024).

        Returns:
            Dict with keys: position_allocation, age_distribution, star_concentration.
        """
        return _SB_TEMPLATE

    def calculate_similarity_score(
        self, roster: List[PlayerAsset]
    ) -> Dict:
        """Compare roster metrics against the SB winner template.

        Uses mean absolute percentage deviation within each category, capped at 1.0.
        Weights: position 50%, age 30%, concentration 20%.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict with keys: position_similarity, age_similarity,
            concentration_similarity, overall_similarity (all 0–100), and gaps (List[str]).
        """
        template = self.build_sb_template()
        pos_alloc = self.calculate_position_allocation(roster)
        age_dist = self.calculate_age_distribution(roster)
        concentration = self.calculate_star_concentration(roster)

        def _similarity(actual: Dict[str, float], target: Dict[str, float]) -> float:
            deviations = []
            for key in target:
                t = target[key]
                a = actual.get(key, 0.0)
                if t > 0:
                    deviations.append(abs(a - t) / t)
                else:
                    deviations.append(0.0 if a == 0 else 1.0)
            mean_dev = sum(deviations) / len(deviations) if deviations else 0.0
            return round(100.0 * max(0.0, 1.0 - min(mean_dev, 1.0)), 2)

        pos_sim = _similarity(pos_alloc, template["position_allocation"])
        age_sim = _similarity(age_dist, template["age_distribution"])
        con_sim = _similarity(concentration, template["star_concentration"])
        overall = round(0.50 * pos_sim + 0.30 * age_sim + 0.20 * con_sim, 2)

        # Build human-readable gap descriptions
        gaps: List[str] = []
        for group, target_pct in template["position_allocation"].items():
            actual_pct = pos_alloc.get(group, 0.0)
            diff = actual_pct - target_pct
            if abs(diff) >= 1.0:
                direction = "overfunded" if diff > 0 else "underfunded"
                gaps.append(
                    f"{group} {direction} by {abs(diff):.1f}% vs SB template "
                    f"({actual_pct:.1f}% vs {target_pct:.1f}%)"
                )

        return {
            "position_similarity": pos_sim,
            "age_similarity": age_sim,
            "concentration_similarity": con_sim,
            "overall_similarity": overall,
            "gaps": gaps,
        }


if __name__ == "__main__":
    from src.player_valuation import PlayerValuationModel

    demo_roster = [
        PlayerAsset("sf_qb_demo", "Demo QB", "QB", "SF", 27,
                    37_750_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("sf_wr_demo", "Demo WR", "WR", "SF", 25,
                    24_900_000, 3, 15_000_000, 120_000_000, 22.0, 900, 2),
        PlayerAsset("sf_ot_demo", "Demo OT", "OT", "SF", 35,
                    23_750_000, 1, 5_000_000, 30_000_000, 0.0, 1050, 0),
        PlayerAsset("sf_edge_demo", "Demo EDGE", "EDGE", "SF", 28,
                    34_000_000, 5, 25_000_000, 170_000_000, 18.0, 800, 3),
    ]

    model = PlayerValuationModel()
    valued = model.value_roster(demo_roster)
    analyzer = SuperBowlTemplateAnalyzer()

    print("Position allocation:", analyzer.calculate_position_allocation(valued))
    print("Age distribution:", analyzer.calculate_age_distribution(valued))
    print("Star concentration:", analyzer.calculate_star_concentration(valued))
    score = analyzer.calculate_similarity_score(valued)
    print(f"Similarity: {score['overall_similarity']:.1f}/100")
    for gap in score["gaps"]:
        print(f"  {gap}")
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_sb_template.py -v
```

Expected: all 16 tests pass.

- [ ] **Step 5: Update CLAUDE.md architecture listing**

In `CLAUDE.md`, find the `src/` architecture block and add `nfc_west_comparison.py` after `visualizations.py`:

```
│   ├── nfc_west_comparison.py       # 🔧 TODO - Division comparison framework
```

- [ ] **Step 6: Commit**

```bash
git add src/sb_template.py tests/test_sb_template.py CLAUDE.md
git commit -m "feat: add SuperBowlTemplateAnalyzer with similarity scoring"
```

---

### Task 2: `src/portfolio_optimizer.py`

**Files:**
- Create: `src/portfolio_optimizer.py`
- Create: `tests/test_portfolio_optimizer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_portfolio_optimizer.py`:

```python
import pytest
import pandas as pd
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.evolution_engine import RosterConstraints
from src.portfolio_optimizer import PortfolioOptimizer


def _make_player(position, cap_hit, age, name="Test", team="SF",
                 epa=5.0, expected_value=0.0, risk_score=0.2):
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=epa, snaps_played=800, games_missed=1,
    )
    p.expected_value = expected_value
    p.risk_score = risk_score
    p.fair_value = expected_value * (1 - risk_score)
    p.efficiency_ratio = expected_value / cap_hit if cap_hit > 0 else 0.0
    return p


@pytest.fixture
def small_roster():
    """Minimal valued roster for testing."""
    model = PlayerValuationModel()
    players = [
        PlayerAsset("sf_qb_p", "Purdy", "QB", "SF", 27,
                    23_000_000, 4, 10_000_000, 90_000_000, 45.0, 1050, 0),
        PlayerAsset("sf_wr_a", "Aiyuk", "WR", "SF", 26,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
    ]
    return model.value_roster(players)


@pytest.fixture
def simple_constraints():
    """Very loose constraints for testing (not real NFL)."""
    c = RosterConstraints()
    c.min_roster_size = 2
    c.max_roster_size = 4
    c.salary_cap = 200_000_000
    c.position_limits = {
        "QB": (1, 2),
        "WR": (1, 2),
    }
    return c


# ---- Constructor -----------------------------------------------------------

def test_constructor_defaults(small_roster):
    opt = PortfolioOptimizer(current_roster=small_roster)
    assert opt._available_players == []


def test_constructor_none_available_treated_as_empty(small_roster):
    opt = PortfolioOptimizer(current_roster=small_roster, available_players=None)
    assert opt._available_players == []


def test_constructor_values_players(small_roster):
    """Players passed in get their expected_value set by the constructor."""
    raw = [
        PlayerAsset("sf_qb_x", "Raw", "QB", "SF", 27,
                    20_000_000, 3, 10_000_000, 60_000_000, 30.0, 900, 0),
    ]
    # expected_value starts at 0 for a fresh PlayerAsset
    assert raw[0].expected_value == 0.0
    opt = PortfolioOptimizer(current_roster=raw)
    # After init, expected_value should be set
    assert opt._current_roster[0].expected_value != 0.0


# ---- identify_pareto_optimal_players ---------------------------------------

def test_pareto_optimal_excludes_dominated_player():
    """Player B dominated by A (A: higher value AND lower cost)."""
    model = PlayerValuationModel()
    players = [
        PlayerAsset("p_a", "A", "QB", "SF", 25, 10_000_000, 2, 5_000_000, 20_000_000, 50.0, 1000, 0),
        PlayerAsset("p_b", "B", "QB", "SF", 25, 20_000_000, 2, 10_000_000, 40_000_000, 20.0, 800, 0),
        PlayerAsset("p_c", "C", "QB", "SF", 25, 25_000_000, 2, 12_000_000, 50_000_000, 80.0, 1050, 0),
    ]
    valued = model.value_roster(players)
    opt = PortfolioOptimizer(current_roster=valued)
    pareto = opt.identify_pareto_optimal_players(valued)
    pareto_names = {p.name for p in pareto}
    # B has lower value than A and higher cost → dominated by A
    assert "B" not in pareto_names
    assert "A" in pareto_names
    assert "C" in pareto_names


def test_pareto_optimal_single_player_always_optimal():
    model = PlayerValuationModel()
    players = [
        PlayerAsset("p_a", "OnlyOne", "QB", "SF", 25,
                    10_000_000, 2, 5_000_000, 20_000_000, 50.0, 1000, 0),
    ]
    valued = model.value_roster(players)
    opt = PortfolioOptimizer(current_roster=valued)
    pareto = opt.identify_pareto_optimal_players(valued)
    assert len(pareto) == 1


# ---- calculate_marginal_value ---------------------------------------------

def test_marginal_value_returns_float(small_roster, simple_constraints):
    opt = PortfolioOptimizer(
        current_roster=small_roster,
        constraints=simple_constraints,
    )
    model = PlayerValuationModel()
    candidate = model.value_roster([
        PlayerAsset("sf_qb_new", "New QB", "QB", "SF", 24,
                    15_000_000, 3, 7_000_000, 45_000_000, 60.0, 1050, 0)
    ])[0]
    result = opt.calculate_marginal_value(small_roster, candidate)
    assert isinstance(result, float)


def test_marginal_value_zero_when_no_position_match(small_roster, simple_constraints):
    opt = PortfolioOptimizer(
        current_roster=small_roster,
        constraints=simple_constraints,
    )
    model = PlayerValuationModel()
    # TE not in simple_roster — no same-position player to replace
    te_candidate = model.value_roster([
        PlayerAsset("sf_te_x", "TE Guy", "TE", "SF", 28,
                    10_000_000, 2, 5_000_000, 20_000_000, 15.0, 700, 1)
    ])[0]
    result = opt.calculate_marginal_value(small_roster, te_candidate)
    assert result == 0.0


# ---- calculate_efficient_frontier -----------------------------------------

def test_efficient_frontier_returns_dataframe(small_roster, simple_constraints):
    opt = PortfolioOptimizer(
        current_roster=small_roster,
        constraints=simple_constraints,
    )
    df = opt.calculate_efficient_frontier(n_points=5)
    assert isinstance(df, pd.DataFrame)
    assert set(["risk", "efficiency", "return_value", "cap_utilization"]).issubset(
        set(df.columns)
    )


def test_efficient_frontier_n_points_respected(small_roster, simple_constraints):
    opt = PortfolioOptimizer(
        current_roster=small_roster,
        constraints=simple_constraints,
    )
    df = opt.calculate_efficient_frontier(n_points=3)
    assert len(df) <= 3


# ---- calculate_position_efficient_allocation ------------------------------

def test_position_efficient_allocation_keys(small_roster, simple_constraints):
    opt = PortfolioOptimizer(
        current_roster=small_roster,
        constraints=simple_constraints,
    )
    result = opt.calculate_position_efficient_allocation()
    assert isinstance(result, dict)
    # Should have entries for at least the positions present in roster
    for group_data in result.values():
        assert set(group_data.keys()) == {
            "current_pct", "optimal_pct", "delta", "recommendation"
        }
        assert group_data["recommendation"] in ("increase", "decrease", "maintain")
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
conda run -n nfl_analytics pytest tests/test_portfolio_optimizer.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'src.portfolio_optimizer'`

- [ ] **Step 3: Implement `src/portfolio_optimizer.py`**

```python
import logging
import random
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.evolution_engine import RosterConstraints
from src.player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer
from src.sb_template import POSITION_GROUPS, _POS_TO_GROUP

logger = logging.getLogger(__name__)

_N_MONTE_CARLO = 1000


class PortfolioOptimizer:
    """Portfolio theory analysis for NFL roster construction.

    Mirrors EvolutionEngine's two-list + constraints constructor pattern.
    Runs PlayerValuationModel on all inputs at init so downstream methods
    receive pre-valued PlayerAsset objects.
    """

    def __init__(
        self,
        current_roster: List[PlayerAsset],
        available_players: Optional[List[PlayerAsset]] = None,
        constraints: Optional[RosterConstraints] = None,
    ) -> None:
        """Initialise and value all input players.

        Args:
            current_roster: The team's current 53-man roster.
            available_players: Additional players to draw from in Monte Carlo
                simulations. Defaults to [] if None.
            constraints: Roster rules. Defaults to standard NFL RosterConstraints().
        """
        self._constraints = constraints if constraints is not None else RosterConstraints()
        self._available_players: List[PlayerAsset] = (
            [] if available_players is None else list(available_players)
        )
        model = PlayerValuationModel()
        self._current_roster = model.value_roster(list(current_roster))
        if self._available_players:
            self._available_players = model.value_roster(self._available_players)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

        for player in shuffled:
            pos = player.position
            _, max_c = self._constraints.position_limits.get(pos, (0, 0))
            if (pos_counts.get(pos, 0) < max_c
                    and cap_used + player.cap_hit_2026 <= self._constraints.salary_cap
                    and len(roster) < self._constraints.max_roster_size):
                roster.append(player)
                pos_counts[pos] = pos_counts.get(pos, 0) + 1
                cap_used += player.cap_hit_2026

        if self._is_valid_roster(roster):
            return roster
        return None

    def _roster_metrics(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return risk, efficiency, return_value, cap_utilization for a roster."""
        analyzer = PortfolioAnalyzer(roster)
        return {
            "risk": analyzer.portfolio_risk(),
            "efficiency": analyzer.portfolio_efficiency(),
            "return_value": analyzer.total_value(),
            "cap_utilization": analyzer.total_cost() / self._constraints.salary_cap,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_efficient_frontier(
        self, n_points: int = 20
    ) -> pd.DataFrame:
        """Monte Carlo efficient frontier over current_roster + available_players.

        Generates up to 1000 random valid rosters, then extracts n_points
        frontier points by binning on risk and taking max-efficiency per bin.

        Args:
            n_points: Number of frontier points to return.

        Returns:
            DataFrame with columns: risk, efficiency, return_value, cap_utilization.
            May have fewer than n_points rows if the player pool is small.
        """
        pool = self._current_roster + self._available_players
        samples: List[Dict[str, float]] = []

        for _ in range(_N_MONTE_CARLO):
            roster = self._random_roster(pool)
            if roster is not None:
                samples.append(self._roster_metrics(roster))

        if not samples:
            logger.warning(
                "Monte Carlo produced 0 valid rosters — check player pool size and constraints"
            )
            return pd.DataFrame(columns=["risk", "efficiency", "return_value", "cap_utilization"])

        df = pd.DataFrame(samples)

        # Bin by risk into n_points equal-width bins; take max efficiency per bin
        df["_bin"] = pd.cut(df["risk"], bins=n_points, labels=False)
        frontier = (
            df.sort_values("efficiency", ascending=False)
            .groupby("_bin", observed=True)
            .first()
            .reset_index(drop=True)
            [["risk", "efficiency", "return_value", "cap_utilization"]]
        )
        return frontier.sort_values("risk").reset_index(drop=True)

    def calculate_position_efficient_allocation(
        self,
    ) -> Dict[str, Dict[str, object]]:
        """Compare current position cap allocation to the optimal from top-10% MC rosters.

        Args: None (uses self._current_roster and self._available_players).

        Returns:
            Dict mapping position group → {current_pct, optimal_pct, delta, recommendation}.
        """
        frontier_df = self.calculate_efficient_frontier(n_points=20)
        if frontier_df.empty:
            return {}

        # Top 10% efficiency threshold
        threshold = frontier_df["efficiency"].quantile(0.90)
        top_rosters = frontier_df[frontier_df["efficiency"] >= threshold]

        # Approximate optimal: use the max-efficiency point's cap distribution
        # (we stored per-roster allocation in the Monte Carlo, but kept only metrics;
        # re-run a targeted small MC to get position data for top-efficiency rosters)
        pool = self._current_roster + self._available_players
        pos_data: Dict[str, List[float]] = {g: [] for g in POSITION_GROUPS}

        for _ in range(200):
            roster = self._random_roster(pool)
            if roster is None:
                continue
            metrics = self._roster_metrics(roster)
            if metrics["efficiency"] >= threshold:
                total_cap = sum(p.cap_hit_2026 for p in roster)
                if total_cap == 0:
                    continue
                group_cap: Dict[str, float] = {g: 0.0 for g in POSITION_GROUPS}
                for p in roster:
                    g = _POS_TO_GROUP.get(p.position.upper().strip())
                    if g:
                        group_cap[g] += p.cap_hit_2026
                for g, cap in group_cap.items():
                    pos_data[g].append(cap / total_cap * 100)

        # Current roster allocation
        from src.sb_template import SuperBowlTemplateAnalyzer
        current_alloc = SuperBowlTemplateAnalyzer().calculate_position_allocation(
            self._current_roster
        )

        result: Dict[str, Dict[str, object]] = {}
        for group in POSITION_GROUPS:
            current_pct = current_alloc.get(group, 0.0)
            optimal_pct = float(np.mean(pos_data[group])) if pos_data[group] else current_pct
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

        Replaces the lowest-expected_value player at the same position as
        the candidate. Returns 0.0 if no same-position player exists.

        Args:
            current_roster: Current roster as a list of valued PlayerAsset objects.
            candidate: The player to evaluate.

        Returns:
            Delta in portfolio_efficiency (positive = improvement).
        """
        same_pos = [
            p for p in current_roster if p.position == candidate.position
        ]
        if not same_pos:
            return 0.0

        weakest = min(same_pos, key=lambda p: p.expected_value)
        new_roster = [p for p in current_roster if p is not weakest] + [candidate]

        before = PortfolioAnalyzer(current_roster).portfolio_efficiency()
        after = PortfolioAnalyzer(new_roster).portfolio_efficiency()
        return round(after - before, 6)


if __name__ == "__main__":
    from src.player_valuation import PlayerValuationModel
    from src.evolution_engine import RosterConstraints

    demo = [
        PlayerAsset("sf_qb_d", "Demo QB", "QB", "SF", 27,
                    37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("sf_wr_d", "Demo WR", "WR", "SF", 25,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
    ]
    c = RosterConstraints()
    c.min_roster_size = 2
    c.max_roster_size = 3
    c.salary_cap = 200_000_000
    c.position_limits = {"QB": (1, 2), "WR": (1, 2)}

    opt = PortfolioOptimizer(current_roster=demo, constraints=c)
    pareto = opt.identify_pareto_optimal_players(opt._current_roster)
    print(f"Pareto optimal players: {[p.name for p in pareto]}")

    candidate = PlayerValuationModel().value_roster([
        PlayerAsset("sf_qb_new", "Better QB", "QB", "SF", 24,
                    20_000_000, 3, 10_000_000, 80_000_000, 60.0, 1050, 0)
    ])[0]
    mv = opt.calculate_marginal_value(opt._current_roster, candidate)
    print(f"Marginal value of Better QB: {mv:+.4f}")
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_portfolio_optimizer.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/portfolio_optimizer.py tests/test_portfolio_optimizer.py
git commit -m "feat: add PortfolioOptimizer with efficient frontier and Pareto analysis"
```

---

### Task 3: `src/visualizations.py`

**Files:**
- Create: `src/visualizations.py`
- Create: `tests/test_visualizations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_visualizations.py`:

```python
import pytest
import plotly.graph_objects as go
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.sb_template import SuperBowlTemplateAnalyzer
from src.visualizations import (
    plot_roster_efficiency_scatter,
    plot_position_allocation_comparison,
    plot_evolution_history,
    plot_player_value_scatter,
    plot_sb_similarity_radar,
    plot_age_distribution,
)


def _make_valued_player(position, cap_hit, age, name="P", team="SF"):
    model = PlayerValuationModel()
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower()}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )
    return model.value_roster([p])[0]


@pytest.fixture
def sf_roster():
    return [
        _make_valued_player("QB", 30_000_000, 27, "Purdy", "SF"),
        _make_valued_player("WR", 20_000_000, 25, "Aiyuk", "SF"),
        _make_valued_player("OT", 15_000_000, 35, "Williams", "SF"),
    ]


@pytest.fixture
def teams_data(sf_roster):
    sea = [_make_valued_player("QB", 25_000_000, 28, "Geno", "SEA")]
    return {"SF": sf_roster, "SEA": sea}


@pytest.fixture
def sb_template():
    return SuperBowlTemplateAnalyzer().build_sb_template()


def test_plot_roster_efficiency_scatter_returns_figure(teams_data):
    fig = plot_roster_efficiency_scatter(teams_data)
    assert isinstance(fig, go.Figure)


def test_plot_position_allocation_comparison_returns_figure(teams_data, sb_template):
    fig = plot_position_allocation_comparison(teams_data, sb_template)
    assert isinstance(fig, go.Figure)


def test_plot_evolution_history_returns_figure():
    history = [
        {"generation": 0, "best_fitness": 0.5, "avg_fitness": 0.3},
        {"generation": 1, "best_fitness": 0.7, "avg_fitness": 0.4},
        {"generation": 2, "best_fitness": 0.7, "avg_fitness": 0.5},
    ]
    fig = plot_evolution_history(history)
    assert isinstance(fig, go.Figure)


def test_plot_player_value_scatter_returns_figure(sf_roster):
    fig = plot_player_value_scatter(sf_roster, highlight_team="SF")
    assert isinstance(fig, go.Figure)


def test_plot_sb_similarity_radar_returns_figure(teams_data, sb_template):
    fig = plot_sb_similarity_radar(teams_data, sb_template)
    assert isinstance(fig, go.Figure)


def test_plot_age_distribution_returns_figure(sf_roster):
    fig = plot_age_distribution(sf_roster)
    assert isinstance(fig, go.Figure)


def test_plot_evolution_history_empty_returns_figure():
    fig = plot_evolution_history([])
    assert isinstance(fig, go.Figure)


def test_plot_roster_efficiency_scatter_empty_dict():
    fig = plot_roster_efficiency_scatter({})
    assert isinstance(fig, go.Figure)
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
conda run -n nfl_analytics pytest tests/test_visualizations.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'src.visualizations'`

- [ ] **Step 3: Implement `src/visualizations.py`**

```python
import logging
from typing import Dict, List

import plotly.graph_objects as go

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.sb_template import (
    POSITION_GROUPS,
    SuperBowlTemplateAnalyzer,
)

logger = logging.getLogger(__name__)

_TEAM_COLORS = {
    "SF": "#AA0000",
    "SEA": "#002244",
    "LAR": "#003594",
    "ARI": "#97233F",
    "KC":  "#E31837",
    "TB":  "#D50A0A",
    "PHI": "#004C54",
}
_DEFAULT_COLOR = "#888888"


def _team_color(team: str) -> str:
    return _TEAM_COLORS.get(team.upper(), _DEFAULT_COLOR)


def plot_roster_efficiency_scatter(
    teams_data: Dict[str, List[PlayerAsset]],
) -> go.Figure:
    """Scatter plot of portfolio risk vs efficiency, one point per team.

    Includes a shaded 'SB Winner Zone' (risk < 0.25, efficiency > 1.15).

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    # SB Winner Zone
    fig.add_shape(
        type="rect",
        x0=0, x1=0.25, y0=1.15, y1=2.0,
        fillcolor="rgba(255, 215, 0, 0.15)",
        line=dict(color="gold", dash="dash"),
        layer="below",
    )
    fig.add_annotation(
        x=0.125, y=1.9, text="SB Winner Zone",
        showarrow=False, font=dict(color="goldenrod", size=11),
    )

    for team, roster in teams_data.items():
        if not roster:
            continue
        analyzer = PortfolioAnalyzer(roster)
        fig.add_trace(go.Scatter(
            x=[analyzer.portfolio_risk()],
            y=[analyzer.portfolio_efficiency()],
            mode="markers+text",
            marker=dict(size=14, color=_team_color(team)),
            text=[team],
            textposition="top center",
            name=team,
        ))

    fig.update_layout(
        title="NFC West — Portfolio Risk vs Efficiency",
        xaxis_title="Portfolio Risk (lower = better)",
        yaxis_title="Portfolio Efficiency (value / cost)",
        showlegend=False,
    )
    return fig


def plot_position_allocation_comparison(
    teams_data: Dict[str, List[PlayerAsset]],
    sb_template: Dict,
) -> go.Figure:
    """Grouped bar chart of position group cap allocation across teams + SB template.

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.
        sb_template: Output of SuperBowlTemplateAnalyzer.build_sb_template().

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()
    analyzer = SuperBowlTemplateAnalyzer()
    groups = list(POSITION_GROUPS.keys())

    for team, roster in teams_data.items():
        alloc = analyzer.calculate_position_allocation(roster)
        fig.add_trace(go.Bar(
            name=team,
            x=groups,
            y=[alloc.get(g, 0) for g in groups],
            marker_color=_team_color(team),
        ))

    # SB template as a bar group
    template_alloc = sb_template["position_allocation"]
    fig.add_trace(go.Bar(
        name="SB Template",
        x=groups,
        y=[template_alloc.get(g, 0) for g in groups],
        marker_color="rgba(255, 215, 0, 0.7)",
        marker_line=dict(color="goldenrod", width=1.5),
    ))

    fig.update_layout(
        barmode="group",
        title="Cap Allocation by Position Group vs SB Template",
        xaxis_title="Position Group",
        yaxis_title="% of Cap",
    )
    return fig


def plot_evolution_history(history: List[Dict]) -> go.Figure:
    """Dual line chart of best and avg fitness over evolution generations.

    Annotates the generation where best_fitness first reaches its maximum.

    Args:
        history: List of dicts with keys generation, best_fitness, avg_fitness.
            This is the history list returned by EvolutionEngine.evolve().

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if not history:
        fig.update_layout(title="Evolution History (no data)")
        return fig

    gens = [h["generation"] for h in history]
    best = [h["best_fitness"] for h in history]
    avg = [h["avg_fitness"] for h in history]

    fig.add_trace(go.Scatter(x=gens, y=best, mode="lines", name="Best Fitness",
                             line=dict(color="#AA0000", width=2)))
    fig.add_trace(go.Scatter(x=gens, y=avg, mode="lines", name="Avg Fitness",
                             line=dict(color="#666666", dash="dot")))

    # Annotate peak generation
    peak_idx = best.index(max(best))
    fig.add_annotation(
        x=gens[peak_idx], y=best[peak_idx],
        text=f"Peak gen {gens[peak_idx]}",
        showarrow=True, arrowhead=2,
    )

    fig.update_layout(
        title="Evolution Fitness History",
        xaxis_title="Generation",
        yaxis_title="Fitness Score",
    )
    return fig


def plot_player_value_scatter(
    players: List[PlayerAsset],
    highlight_team: str = "SF",
) -> go.Figure:
    """Scatter of cap_hit_2026 vs expected_value, colored by over/under-valued.

    Green = undervalued (value > cap * 1.15), red = overvalued (cap > value * 1.15),
    grey = fair value. Marker size inversely proportional to risk_score.
    Labels the top 3 most over- and undervalued players.

    Args:
        players: List of valued PlayerAsset objects.
        highlight_team: Team abbreviation used in the chart title.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if not players:
        fig.update_layout(title="Player Value vs Cap Hit")
        return fig

    max_cap = max((p.cap_hit_2026 for p in players), default=1)

    # Fair value diagonal
    fig.add_trace(go.Scatter(
        x=[0, max_cap * 1.1],
        y=[0, max_cap * 1.1],
        mode="lines",
        name="Fair Value",
        line=dict(color="grey", dash="dash"),
        showlegend=False,
    ))

    overvalued = sorted(
        [p for p in players if p.cap_hit_2026 > p.expected_value * 1.15 and p.expected_value > 0],
        key=lambda p: p.cap_hit_2026 - p.expected_value, reverse=True
    )[:3]
    undervalued = sorted(
        [p for p in players if p.expected_value > p.cap_hit_2026 * 1.15],
        key=lambda p: p.expected_value - p.cap_hit_2026, reverse=True
    )[:3]
    label_ids = {p.player_id for p in overvalued + undervalued}

    for player in players:
        if player.cap_hit_2026 <= 0 or player.expected_value <= 0:
            continue
        if player.cap_hit_2026 > player.expected_value * 1.15:
            color = "red"
        elif player.expected_value > player.cap_hit_2026 * 1.15:
            color = "green"
        else:
            color = "grey"

        size = max(6, 20 * (1 - player.risk_score))
        label = player.name if player.player_id in label_ids else ""

        fig.add_trace(go.Scatter(
            x=[player.cap_hit_2026],
            y=[player.expected_value],
            mode="markers+text" if label else "markers",
            marker=dict(size=size, color=color, opacity=0.7),
            text=label,
            textposition="top center",
            name=player.name,
            showlegend=False,
        ))

    fig.update_layout(
        title=f"{highlight_team} — Player Value vs Cap Hit",
        xaxis_title="Cap Hit 2026 ($)",
        yaxis_title="Expected Value ($)",
    )
    return fig


def plot_sb_similarity_radar(
    teams_data: Dict[str, List[PlayerAsset]],
    sb_template: Dict,
) -> go.Figure:
    """Radar chart comparing teams to the SB template on 5 structural axes.

    Axes: QB spend %, Skill spend %, OL spend %, Age 26-29 %, Top-5 cap concentration %.

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.
        sb_template: Output of SuperBowlTemplateAnalyzer.build_sb_template().

    Returns:
        Plotly Figure.
    """
    axes = ["QB spend", "Skill spend", "OL spend", "Age 26-29", "Top-5 cap"]
    fig = go.Figure()
    analyzer = SuperBowlTemplateAnalyzer()

    def _radar_values(roster: List[PlayerAsset]) -> List[float]:
        alloc = analyzer.calculate_position_allocation(roster)
        age = analyzer.calculate_age_distribution(roster)
        conc = analyzer.calculate_star_concentration(roster)
        return [
            alloc.get("QB", 0),
            alloc.get("SKILL", 0),
            alloc.get("OL", 0),
            age.get("26-29", 0),
            conc.get("top_5", 0),
        ]

    for team, roster in teams_data.items():
        if not roster:
            continue
        vals = _radar_values(roster)
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            fillcolor=_team_color(team).replace(")", ", 0.1)").replace("rgb", "rgba"),
            name=team,
            line=dict(color=_team_color(team)),
        ))

    # SB Template trace
    template_vals = [
        sb_template["position_allocation"].get("QB", 0),
        sb_template["position_allocation"].get("SKILL", 0),
        sb_template["position_allocation"].get("OL", 0),
        sb_template["age_distribution"].get("26-29", 0),
        sb_template["star_concentration"].get("top_5", 0),
    ]
    fig.add_trace(go.Scatterpolar(
        r=template_vals + [template_vals[0]],
        theta=axes + [axes[0]],
        fill="toself",
        fillcolor="rgba(255, 215, 0, 0.15)",
        name="SB Template",
        line=dict(color="goldenrod", dash="dash"),
    ))

    fig.update_layout(
        title="SB Template Similarity Radar",
        polar=dict(radialaxis=dict(visible=True, range=[0, 50])),
    )
    return fig


def plot_age_distribution(roster: List[PlayerAsset]) -> go.Figure:
    """Grouped bar chart comparing roster age distribution to the SB template.

    Args:
        roster: List of PlayerAsset objects.

    Returns:
        Plotly Figure.
    """
    analyzer = SuperBowlTemplateAnalyzer()
    buckets = ["22-25", "26-29", "30+"]
    roster_dist = analyzer.calculate_age_distribution(roster)
    template_dist = analyzer.build_sb_template()["age_distribution"]

    fig = go.Figure([
        go.Bar(
            name="Current Roster",
            x=buckets,
            y=[roster_dist.get(b, 0) for b in buckets],
            marker_color="#AA0000",
        ),
        go.Bar(
            name="SB Template",
            x=buckets,
            y=[template_dist.get(b, 0) for b in buckets],
            marker_color="rgba(255, 215, 0, 0.7)",
            marker_line=dict(color="goldenrod", width=1.5),
        ),
    ])

    fig.update_layout(
        barmode="group",
        title="Age Distribution vs SB Template",
        xaxis_title="Age Bucket",
        yaxis_title="% of Roster",
    )
    return fig


if __name__ == "__main__":
    from src.player_valuation import PlayerValuationModel

    model = PlayerValuationModel()
    demo_players = [
        PlayerAsset("sf_qb_d", "Purdy", "QB", "SF", 27,
                    37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("sf_wr_d", "Aiyuk", "WR", "SF", 26,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
        PlayerAsset("sea_qb_d", "Geno", "QB", "SEA", 33,
                    20_000_000, 1, 10_000_000, 20_000_000, 15.0, 900, 2),
    ]
    valued = model.value_roster(demo_players)
    teams = {"SF": [p for p in valued if p.team == "SF"],
             "SEA": [p for p in valued if p.team == "SEA"]}
    template = SuperBowlTemplateAnalyzer().build_sb_template()

    fig = plot_roster_efficiency_scatter(teams)
    print(f"Efficiency scatter: {len(fig.data)} traces")

    fig2 = plot_age_distribution(teams["SF"])
    print(f"Age distribution: {len(fig2.data)} traces")
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_visualizations.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/visualizations.py tests/test_visualizations.py
git commit -m "feat: add six Plotly visualization functions"
```

---

### Task 4: `src/nfc_west_comparison.py`

**Files:**
- Create: `src/nfc_west_comparison.py`
- Create: `tests/test_nfc_west_comparison.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_nfc_west_comparison.py`:

```python
import pytest
import pandas as pd
import plotly.graph_objects as go
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.nfc_west_comparison import DivisionAnalyzer


def _make_player(position, cap_hit, age, name="P", team="SF"):
    return PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )


@pytest.fixture
def two_team_data():
    return {
        "SF": [
            _make_player("QB", 30_000_000, 27, "Purdy", "SF"),
            _make_player("WR", 20_000_000, 25, "Aiyuk", "SF"),
            _make_player("OT", 15_000_000, 35, "Williams", "SF"),
        ],
        "SEA": [
            _make_player("QB", 25_000_000, 33, "Geno", "SEA"),
            _make_player("WR", 18_000_000, 27, "Metcalf", "SEA"),
        ],
    }


@pytest.fixture
def analyzer(two_team_data):
    return DivisionAnalyzer(two_team_data)


# ---- Constructor -----------------------------------------------------------

def test_constructor_values_all_rosters(two_team_data):
    da = DivisionAnalyzer(two_team_data)
    for team, roster in da._valued_rosters.items():
        assert all(p.expected_value != 0.0 for p in roster)


# ---- compare_portfolio_metrics --------------------------------------------

def test_compare_portfolio_metrics_returns_dataframe(analyzer):
    df = analyzer.compare_portfolio_metrics()
    assert isinstance(df, pd.DataFrame)


def test_compare_portfolio_metrics_columns(analyzer):
    df = analyzer.compare_portfolio_metrics()
    required = {"team", "total_value", "total_cost", "efficiency",
                "risk", "sharpe_ratio", "avg_age", "num_overvalued"}
    assert required.issubset(set(df.columns))


def test_compare_portfolio_metrics_one_row_per_team(analyzer, two_team_data):
    df = analyzer.compare_portfolio_metrics()
    assert len(df) == len(two_team_data)


# ---- compare_position_allocation ------------------------------------------

def test_compare_position_allocation_returns_dataframe(analyzer):
    df = analyzer.compare_position_allocation()
    assert isinstance(df, pd.DataFrame)


def test_compare_position_allocation_has_position_columns(analyzer):
    df = analyzer.compare_position_allocation()
    from src.sb_template import POSITION_GROUPS
    for group in POSITION_GROUPS:
        assert group in df.columns


# ---- rank_teams -----------------------------------------------------------

def test_rank_teams_default_metric(analyzer):
    df = analyzer.rank_teams()
    assert "rank" in df.columns
    assert "efficiency" in df.columns
    assert set(df["rank"].tolist()) == set(range(1, len(df) + 1))


def test_rank_teams_valid_metrics(analyzer):
    for metric in ("efficiency", "risk", "sharpe_ratio", "sb_similarity"):
        df = analyzer.rank_teams(metric=metric)
        assert "rank" in df.columns


def test_rank_teams_risk_ascending(analyzer):
    df = analyzer.rank_teams(metric="risk").sort_values("rank")
    # Rank 1 should have the lowest risk
    assert df.iloc[0]["risk"] <= df.iloc[-1]["risk"]


# ---- identify_division_advantages ----------------------------------------

def test_identify_division_advantages_keys(analyzer):
    result = analyzer.identify_division_advantages(primary_team="SF")
    assert set(result.keys()) == {"strengths", "weaknesses", "opportunities"}


def test_identify_division_advantages_lists_of_strings(analyzer):
    result = analyzer.identify_division_advantages(primary_team="SF")
    for key in ("strengths", "weaknesses", "opportunities"):
        assert isinstance(result[key], list)
        assert all(isinstance(s, str) for s in result[key])


# ---- generate_division_report --------------------------------------------

def test_generate_division_report_keys(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    assert set(report.keys()) == {
        "metrics_df", "allocation_df", "rankings",
        "advantages", "sb_similarity", "figures",
    }


def test_generate_division_report_figures_are_plotly(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    for name, fig in report["figures"].items():
        assert isinstance(fig, go.Figure), f"Figure '{name}' is not a go.Figure"


def test_generate_division_report_figure_keys(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    expected_keys = {
        "efficiency_scatter", "position_allocation",
        "age_distribution", "sb_radar", "player_value_scatter",
    }
    assert set(report["figures"].keys()) == expected_keys
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
conda run -n nfl_analytics pytest tests/test_nfc_west_comparison.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'src.nfc_west_comparison'`

- [ ] **Step 3: Implement `src/nfc_west_comparison.py`**

```python
import logging
from typing import Dict, List

import pandas as pd

from src.nfc_west_comparison import _  # self-import guard — remove this line
# NOTE: remove the line above; it's just a placeholder reminder
```

Replace with the full implementation:

```python
import logging
from typing import Dict, List

import pandas as pd

from src.player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer
from src.sb_template import POSITION_GROUPS, SuperBowlTemplateAnalyzer
from src.visualizations import (
    plot_age_distribution,
    plot_player_value_scatter,
    plot_position_allocation_comparison,
    plot_roster_efficiency_scatter,
    plot_sb_similarity_radar,
)

logger = logging.getLogger(__name__)

_VALID_METRICS = ("efficiency", "risk", "sharpe_ratio", "sb_similarity")


class DivisionAnalyzer:
    """Coordination layer for NFC West division analysis.

    Values all roster inputs at init so downstream methods receive
    pre-valued PlayerAsset objects.
    """

    def __init__(self, teams_data: Dict[str, List[PlayerAsset]]) -> None:
        """Initialise and value all team rosters.

        Args:
            teams_data: Dict mapping team abbreviation (e.g. 'SF') to roster.
        """
        model = PlayerValuationModel()
        self._valued_rosters: Dict[str, List[PlayerAsset]] = {
            team: model.value_roster(list(roster))
            for team, roster in teams_data.items()
        }
        self._sb_analyzer = SuperBowlTemplateAnalyzer()
        self._sb_template = self._sb_analyzer.build_sb_template()

    def compare_portfolio_metrics(self) -> pd.DataFrame:
        """Return one row per team with portfolio-level metrics.

        Returns:
            DataFrame with columns: team, total_value, total_cost, efficiency,
            risk, sharpe_ratio, avg_age, num_overvalued.
        """
        rows = []
        for team, roster in self._valued_rosters.items():
            if not roster:
                continue
            pa = PortfolioAnalyzer(roster)
            summary = pa.summary_report()
            rows.append({
                "team": team,
                "total_value": round(summary["total_value"], 0),
                "total_cost": round(summary["total_cost"], 0),
                "efficiency": round(summary["efficiency"], 4),
                "risk": round(summary["risk"], 4),
                "sharpe_ratio": round(summary["sharpe_ratio"], 4),
                "avg_age": round(summary["avg_roster_age"], 1),
                "num_overvalued": summary["num_overvalued"],
            })
        return pd.DataFrame(rows)

    def compare_position_allocation(self) -> pd.DataFrame:
        """Return cap % per position group for each team.

        Returns:
            DataFrame with team as index and position groups as columns.
        """
        rows = []
        groups = list(POSITION_GROUPS.keys())
        for team, roster in self._valued_rosters.items():
            alloc = self._sb_analyzer.calculate_position_allocation(roster)
            row = {"team": team}
            row.update({g: round(alloc.get(g, 0.0), 2) for g in groups})
            rows.append(row)
        return pd.DataFrame(rows).set_index("team")

    def rank_teams(self, metric: str = "efficiency") -> pd.DataFrame:
        """Rank all teams by a given metric.

        Args:
            metric: One of 'efficiency', 'risk', 'sharpe_ratio', 'sb_similarity'.
                For 'risk', lower is better (ranks ascending).
                All others rank descending.

        Returns:
            DataFrame with columns: team, <metric>, rank.
        """
        if metric not in _VALID_METRICS:
            raise ValueError(f"metric must be one of {_VALID_METRICS}, got '{metric}'")

        if metric == "sb_similarity":
            scores = {
                team: self._sb_analyzer.calculate_similarity_score(roster)["overall_similarity"]
                for team, roster in self._valued_rosters.items()
            }
            df = pd.DataFrame([
                {"team": team, "sb_similarity": score}
                for team, score in scores.items()
            ])
            df = df.sort_values("sb_similarity", ascending=False).reset_index(drop=True)
        else:
            metrics_df = self.compare_portfolio_metrics()
            df = metrics_df[["team", metric]].copy()
            ascending = metric == "risk"
            df = df.sort_values(metric, ascending=ascending).reset_index(drop=True)

        df["rank"] = range(1, len(df) + 1)
        return df

    def identify_division_advantages(
        self, primary_team: str = "SF"
    ) -> Dict[str, List[str]]:
        """Compare primary team's position allocations to the division average.

        Args:
            primary_team: Team abbreviation for the primary team.

        Returns:
            Dict with keys: strengths, weaknesses, opportunities.
            Strengths = groups where primary leads division avg.
            Weaknesses = groups where primary trails.
            Opportunities = weaknesses where primary is ranked 3rd or 4th.
        """
        alloc_df = self.compare_position_allocation()

        if primary_team not in alloc_df.index:
            logger.warning(f"Primary team '{primary_team}' not in teams_data")
            return {"strengths": [], "weaknesses": [], "opportunities": []}

        groups = list(POSITION_GROUPS.keys())
        primary_alloc = alloc_df.loc[primary_team]
        division_avg = alloc_df[groups].mean()

        strengths, weaknesses, opportunities = [], [], []

        for group in groups:
            primary_pct = primary_alloc[group]
            avg_pct = division_avg[group]

            if primary_pct > avg_pct:
                strengths.append(group)
            elif primary_pct < avg_pct:
                weaknesses.append(group)
                # Check rank in this position group (lower cap = worse rank)
                group_series = alloc_df[group].sort_values(ascending=False)
                rank = list(group_series.index).index(primary_team) + 1
                if rank >= 3:
                    opportunities.append(group)

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
        }

    def generate_division_report(
        self, primary_team: str = "SF"
    ) -> Dict:
        """Generate a complete division analysis report.

        Orchestrates all metrics, rankings, and 5 Plotly figures.
        Note: plot_evolution_history is excluded — it requires EvolutionEngine output.

        Args:
            primary_team: Team abbreviation for team-specific figures.

        Returns:
            Dict with keys: metrics_df, allocation_df, rankings, advantages,
            sb_similarity, figures.
        """
        metrics_df = self.compare_portfolio_metrics()
        allocation_df = self.compare_position_allocation()
        advantages = self.identify_division_advantages(primary_team)

        rankings = {m: self.rank_teams(m) for m in _VALID_METRICS}

        sb_similarity = {
            team: self._sb_analyzer.calculate_similarity_score(roster)
            for team, roster in self._valued_rosters.items()
        }

        primary_roster = self._valued_rosters.get(primary_team, [])
        figures = {
            "efficiency_scatter": plot_roster_efficiency_scatter(self._valued_rosters),
            "position_allocation": plot_position_allocation_comparison(
                self._valued_rosters, self._sb_template
            ),
            "age_distribution": plot_age_distribution(primary_roster),
            "sb_radar": plot_sb_similarity_radar(
                self._valued_rosters, self._sb_template
            ),
            "player_value_scatter": plot_player_value_scatter(
                primary_roster, highlight_team=primary_team
            ),
        }

        return {
            "metrics_df": metrics_df,
            "allocation_df": allocation_df,
            "rankings": rankings,
            "advantages": advantages,
            "sb_similarity": sb_similarity,
            "figures": figures,
        }


if __name__ == "__main__":
    from src.player_valuation import PlayerValuationModel

    demo_teams = {
        "SF": [
            PlayerAsset("sf_qb", "Purdy", "QB", "SF", 27,
                        37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
            PlayerAsset("sf_wr", "Aiyuk", "WR", "SF", 26,
                        24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
            PlayerAsset("sf_ot", "Williams", "OT", "SF", 35,
                        23_000_000, 1, 5_000_000, 23_000_000, 0.0, 1050, 0),
        ],
        "SEA": [
            PlayerAsset("sea_qb", "Geno", "QB", "SEA", 33,
                        20_000_000, 1, 10_000_000, 20_000_000, 15.0, 900, 2),
            PlayerAsset("sea_wr", "Metcalf", "WR", "SEA", 27,
                        22_000_000, 3, 11_000_000, 66_000_000, 18.0, 950, 1),
        ],
    }

    da = DivisionAnalyzer(demo_teams)
    print("=== Portfolio Metrics ===")
    print(da.compare_portfolio_metrics().to_string())
    print("\n=== Rankings (efficiency) ===")
    print(da.rank_teams("efficiency").to_string())
    print("\n=== SF Advantages ===")
    adv = da.identify_division_advantages("SF")
    print("Strengths:", adv["strengths"])
    print("Weaknesses:", adv["weaknesses"])
    print("Opportunities:", adv["opportunities"])
    report = da.generate_division_report("SF")
    print(f"\nReport figures: {list(report['figures'].keys())}")
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_nfc_west_comparison.py -v
```

Expected: all 14 tests pass.

- [ ] **Step 5: Run the full test suite**

```bash
conda run -n nfl_analytics pytest tests/ -v --tb=short
```

Expected: all tests across all 7 test files pass.

- [ ] **Step 6: Commit**

```bash
git add src/nfc_west_comparison.py tests/test_nfc_west_comparison.py
git commit -m "feat: add DivisionAnalyzer coordination layer (Priority 3 complete)"
```

---

## Self-Review

**Spec coverage:**
- `POSITION_GROUPS` defined in `sb_template.py`, imported everywhere ✓
- Task 1 — all 5 methods: `calculate_position_allocation`, `calculate_age_distribution`, `calculate_star_concentration`, `build_sb_template`, `calculate_similarity_score` ✓
- Task 1 — similarity weights 50/30/20, gap format, SB template constants ✓
- Task 2 — constructor mirrors EvolutionEngine, `available_players=None→[]` ✓
- Task 2 — all 4 methods: `calculate_efficient_frontier`, `calculate_position_efficient_allocation`, `identify_pareto_optimal_players`, `calculate_marginal_value` ✓
- Task 2 — marginal_value returns 0.0 when no same-position player ✓
- Task 3 — all 6 functions, no class, no `st.*`, all return `go.Figure` ✓
- Task 3 — `plot_player_value_scatter` labels top 3 over/undervalued ✓
- Task 3 — `plot_evolution_history` annotates peak generation ✓
- Task 4 — `DivisionAnalyzer` values rosters at init ✓
- Task 4 — all 5 methods: `compare_portfolio_metrics`, `compare_position_allocation`, `rank_teams`, `identify_division_advantages`, `generate_division_report` ✓
- Task 4 — `rank_teams` risk ascending, others descending ✓
- Task 4 — `generate_division_report` excludes `plot_evolution_history` (noted in docstring) ✓
- CLAUDE.md update ✓
- Each file has `if __name__ == "__main__":` demo block ✓
- All imports absolute, no `print()`, Google-style docstrings, return types annotated ✓

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:** `POSITION_GROUPS` and `_POS_TO_GROUP` defined in `sb_template.py` and imported in `portfolio_optimizer.py` and `nfc_west_comparison.py`. `SuperBowlTemplateAnalyzer` used consistently by name throughout. `PortfolioAnalyzer` always imported from `src.player_valuation`.
