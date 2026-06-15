# Analysis Modules Design
**Date:** 2026-06-15
**Priority:** 3 — Analysis Modules
**Goal:** Four pure-Python analysis modules (no Streamlit) that sit between the data pipeline and the dashboard/AI layer. Implemented in dependency order as sequential tasks.

---

## Overview

All four modules live in `src/`. All imports are absolute from the project root. No `print()` statements — use `logging`. Every public method has a Google-style docstring with `Args:` and `Returns:`. Each file has an `if __name__ == "__main__":` demo block using synthetic `PlayerAsset` data that requires no real data files.

**Dependency order:**
1. `sb_template.py` — no internal dependencies
2. `portfolio_optimizer.py` — depends on `player_valuation.py` only
3. `visualizations.py` — depends on `sb_template.py` and `portfolio_optimizer.py`
4. `nfc_west_comparison.py` — coordination layer; imports all three above

**Primary team:** SF 49ers. Division: SF, SEA, LAR, ARI. SB template teams: KC (2020, 2023, 2024), TB (2021), LAR (2022), PHI (2025).

---

## Position Group Mapping

Used consistently across all four modules:

```python
POSITION_GROUPS = {
    "QB":      ["QB"],
    "SKILL":   ["WR", "RB", "TE"],
    "OL":      ["OT", "OG", "C"],
    "EDGE":    ["EDGE"],
    "DL":      ["DL"],
    "LB":      ["LB"],
    "DB":      ["CB", "S"],
    "SPECIAL": ["K", "P", "LS"],
}
```

---

## Task 1: `src/sb_template.py`

**Class:** `SuperBowlTemplateAnalyzer`

Stateless analysis class. All methods take `List[PlayerAsset]` and return metrics. Does not read data files directly.

### Methods

**`calculate_position_allocation(roster: List[PlayerAsset]) -> Dict[str, float]`**
Returns % of total cap hit allocated to each position group.
Edge cases: empty roster returns all zeros; players with unrecognized positions (e.g., blank position from OTC data) are skipped with a warning and excluded from cap totals.

**`calculate_age_distribution(roster: List[PlayerAsset]) -> Dict[str, float]`**
Returns % of roster count in three age buckets:
- `"22-25"`, `"26-29"`, `"30+"`
Players with `age == 0` are excluded from the count with a warning.

**`calculate_star_concentration(roster: List[PlayerAsset]) -> Dict[str, float]`**
Returns % of total cap held by:
- `"top_5"`: top 5 players by cap hit
- `"top_10"`: top 10 players by cap hit

**`build_sb_template() -> Dict`**
Returns hardcoded averages from recent SB winners (2020–2024).
No parameters — pure constant:

```python
{
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
```

**`calculate_similarity_score(roster: List[PlayerAsset]) -> Dict`**
Compares roster metrics against `build_sb_template()`.
Returns:
```python
{
    "position_similarity": float,    # 0–100
    "age_similarity": float,         # 0–100
    "concentration_similarity": float, # 0–100
    "overall_similarity": float,     # weighted average
    "gaps": List[str],               # human-readable gap descriptions
}
```

Scoring: `similarity = 100 * (1 - normalized_distance)` where normalized distance is the mean absolute percentage deviation across all metrics within a category, capped at 1.0.

Weights: position 50%, age 30%, concentration 20%.

Gap example format: `"OL underfunded by 3.2% vs SB template (12.5% vs 15.0%)"`.

---

## Task 2: `src/portfolio_optimizer.py`

**Class:** `PortfolioOptimizer`

**Constructor:**
```python
def __init__(
    self,
    current_roster: List[PlayerAsset],
    available_players: Optional[List[PlayerAsset]] = None,
    constraints: RosterConstraints = None,
)
```
`available_players=None` is treated as `[]` internally.
`constraints=None` defaults to `RosterConstraints()` (standard 53-man NFL rules).
Constructor runs `PlayerValuationModel().value_roster()` on all input players at init so all downstream methods work on valued assets.

Mirrors `EvolutionEngine`'s two-list + constraints pattern exactly.

### Methods

**`calculate_efficient_frontier(n_points: int = 20) -> pd.DataFrame`**
Monte Carlo over 1000 random valid rosters drawn from `current_roster + available_players`.
Random roster generation: shuffle pool, greedily fill position requirements per `RosterConstraints`, keep if valid.
Returns DataFrame with columns: `risk, efficiency, return_value, cap_utilization`.
The `n_points` frontier points are extracted by binning the 1000 results into equal risk deciles and taking the max-efficiency roster per bin.

**`calculate_position_efficient_allocation() -> Dict[str, Dict]`**
Runs `calculate_efficient_frontier()` internally, identifies the top 10% efficiency rosters, computes their average position group cap allocation, and compares to current roster.
Per position group returns:
```python
{
    "current_pct": float,
    "optimal_pct": float,
    "delta": float,
    "recommendation": "increase" | "decrease" | "maintain",  # ±2% threshold for "maintain"
}
```

**`identify_pareto_optimal_players(available: List[PlayerAsset]) -> List[PlayerAsset]`**
Returns players on the Pareto frontier of `expected_value` vs `cap_hit_2026`.
A player is dominated if another player has both higher `expected_value` AND lower `cap_hit_2026`. Returns all non-dominated players.

**`calculate_marginal_value(current_roster: List[PlayerAsset], candidate: PlayerAsset) -> float`**
Swaps `candidate` into `current_roster` by replacing the lowest-`expected_value` player at the same position.
Returns delta in `PortfolioAnalyzer.portfolio_efficiency()` after swap.
Returns `0.0` if no same-position player exists in current roster.

---

## Task 3: `src/visualizations.py`

Six standalone functions. No class. No `st.*` calls. All return `plotly.graph_objects.Figure`.

**`plot_roster_efficiency_scatter(teams_data: Dict[str, List[PlayerAsset]]) -> go.Figure`**
Scatter: x=`portfolio_risk`, y=`portfolio_efficiency`. One labeled point per team.
"SB Winner Zone" rendered as a shaded `go.Scatter` filled rectangle (approximate: risk < 0.25, efficiency > 1.15).

**`plot_position_allocation_comparison(teams_data: Dict[str, List[PlayerAsset]], sb_template: Dict) -> go.Figure`**
Grouped bar chart. X-axis = 8 position groups. One bar group per team + SB template. Y-axis = % of cap.

**`plot_evolution_history(history: List[Dict]) -> go.Figure`**
Dual line chart: `best_fitness` and `avg_fitness` vs generation.
Each dict in `history` has keys: `generation`, `best_fitness`, `avg_fitness`.
Annotation at the generation where `best_fitness` first reaches its overall max.

**`plot_player_value_scatter(players: List[PlayerAsset], highlight_team: str = "SF") -> go.Figure`**
X=`cap_hit_2026`, Y=`expected_value`. Diagonal line where x==y (fair value).
Color: green=undervalued (value > cap * 1.15), red=overvalued (cap > value * 1.15), grey=fair.
Marker size = `max(6, 20 * (1 - risk_score))` (bigger = lower risk).
Label top 3 most overvalued and top 3 most undervalued by name.

**`plot_sb_similarity_radar(teams_data: Dict[str, List[PlayerAsset]], sb_template: Dict) -> go.Figure`**
Radar/spider chart. 5 axes: QB spend %, Skill spend %, OL spend %, Age 26-29 %, Top-5 cap concentration %.
One trace per team + one trace for SB template. Filled with low opacity.

**`plot_age_distribution(roster: List[PlayerAsset]) -> go.Figure`**
Grouped bar chart. X-axis = 3 age buckets. Two bar groups: current roster % vs SB template %.

---

## Task 4: `src/nfc_west_comparison.py`

**Class:** `DivisionAnalyzer`

Coordination layer. Imports from `sb_template`, `portfolio_optimizer`, `visualizations`, and `player_valuation`.

**Constructor:**
```python
def __init__(self, teams_data: Dict[str, List[PlayerAsset]])
```
Keys are team abbreviations: `"SF"`, `"SEA"`, `"LAR"`, `"ARI"`.
Runs `PlayerValuationModel().value_roster()` on all teams at init.
Stores valued rosters internally as `self._valued_rosters`.

### Methods

**`compare_portfolio_metrics() -> pd.DataFrame`**
One row per team. Columns: `team, total_value, total_cost, efficiency, risk, sharpe_ratio, avg_age, num_overvalued`.
Uses `PortfolioAnalyzer` from `player_valuation.py`.

**`compare_position_allocation() -> pd.DataFrame`**
Rows = teams, columns = 8 position groups + `team` index.
Values = % of cap allocated. Uses `SuperBowlTemplateAnalyzer.calculate_position_allocation()`.

**`rank_teams(metric: str = "efficiency") -> pd.DataFrame`**
Valid metrics: `"efficiency"`, `"risk"`, `"sharpe_ratio"`, `"sb_similarity"`.
For `"sb_similarity"`, calls `SuperBowlTemplateAnalyzer.calculate_similarity_score()` per team.
For `"risk"`, lower is better (ranks ascending). All others rank descending.
Returns DataFrame: columns `team, <metric>, rank`.

**`identify_division_advantages(primary_team: str = "SF") -> Dict`**
Compares primary team's position group cap % to division average.
Returns:
```python
{
    "strengths": List[str],      # position groups where primary leads division avg
    "weaknesses": List[str],     # position groups where primary trails division avg
    "opportunities": List[str],  # weaknesses where adding cap would most improve rank
}
```
"Opportunities" = weaknesses where the primary team's rank in that position group is 3rd or 4th.

**`generate_division_report(primary_team: str = "SF") -> Dict`**
Orchestrates all above methods plus 5 of the 6 Plotly figures. `plot_evolution_history` is excluded — it requires `EvolutionEngine` output which is not available at this layer.
Returns:
```python
{
    "metrics_df": pd.DataFrame,
    "allocation_df": pd.DataFrame,
    "rankings": Dict[str, pd.DataFrame],  # one per metric
    "advantages": Dict,
    "sb_similarity": Dict[str, Dict],     # one per team
    "figures": {
        "efficiency_scatter": go.Figure,
        "position_allocation": go.Figure,
        "age_distribution": go.Figure,    # SF only
        "sb_radar": go.Figure,
        "player_value_scatter": go.Figure, # SF only
    },
}
```

---

## CLAUDE.md Update

Add `src/nfc_west_comparison.py` to the architecture listing in CLAUDE.md under the `src/` directory.

---

## Key Constraints

- Absolute imports throughout (`from src.player_valuation import ...`)
- No `print()` — use `logging`
- Google-style docstrings on all public methods
- Return types always annotated
- Handle empty list inputs gracefully (return zeros/empty DataFrames, log warning)
- No Streamlit calls in any of these files
- Each file has a `if __name__ == "__main__":` demo block with synthetic data
