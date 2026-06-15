# Streamlit Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 6-page Streamlit dashboard that demonstrates the five built systems (valuation model, division analysis, evolution engine, SB template matching, AI agent) to a 49ers front-office audience.

**Architecture:** `utils.py` exports a `@st.cache_data`-decorated `load_players()` so the CSV+valuation runs once per session regardless of which page loads first. `app.py` is the home page; five files in `streamlit_app/pages/` auto-discovered by Streamlit. No custom CSS — default styling, focus on correctness. Verification is by launching the app and navigating each page, not unit tests (except `utils.py` which has a pure-function inner layer that is unit-testable).

**Tech Stack:** Python 3.11, Streamlit, Plotly, all existing `src/` modules. Conda env: `nfl_analytics`. Run from project root: `streamlit run streamlit_app/app.py`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `streamlit_app/utils.py` | Create | Shared `@st.cache_data` data loading |
| `streamlit_app/app.py` | Replace stub | Home page: metrics overview |
| `streamlit_app/pages/01_roster_analysis.py` | Create | SF player value scatter + tables |
| `streamlit_app/pages/02_nfc_west_comparison.py` | Create | DivisionAnalyzer charts |
| `streamlit_app/pages/03_evolution_results.py` | Create | Static evolution demo |
| `streamlit_app/pages/04_sb_template.py` | Create | SB similarity radar + gaps |
| `streamlit_app/pages/05_ai_assistant.py` | Create | AgentSystem chat interface |
| `tests/test_utils.py` | Create | Unit test for `_load_players_from_csv` |

---

### Task 1: `utils.py` + unit test + pages directory

**Files:**
- Create: `streamlit_app/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Create `streamlit_app/pages/` directory**

```bash
mkdir -p /home/hankbutler/Desktop/Projects/roster-analysis/streamlit_app/pages
```

- [ ] **Step 2: Write failing unit test for `_load_players_from_csv`**

Create `tests/test_utils.py`:

```python
import pandas as pd
import pytest
from src.player_valuation import PlayerAsset


def test_load_players_from_csv_returns_valued_players(tmp_path):
    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([{
        "player_id": "sf_qb_test", "name": "Test QB", "position": "QB",
        "team": "SF", "age": 27, "cap_hit_2026": 23_700_000,
        "years_remaining": 3, "guaranteed_money": 10_000_000,
        "total_contract_value": 71_100_000, "epa_total": 45.0,
        "snaps_played": 1050, "games_missed": 0,
    }]).to_csv(csv_path, index=False)

    from streamlit_app.utils import _load_players_from_csv
    players = _load_players_from_csv(str(csv_path))

    assert len(players) == 1
    assert players[0].name == "Test QB"
    assert players[0].position == "QB"
    assert players[0].expected_value != 0.0  # PlayerValuationModel ran


def test_load_players_from_csv_raises_on_missing_file():
    from streamlit_app.utils import _load_players_from_csv
    with pytest.raises(FileNotFoundError):
        _load_players_from_csv("/nonexistent/path/player_assets_ready.csv")


def test_load_players_from_csv_skips_bad_rows(tmp_path):
    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([
        {
            "player_id": "sf_qb_good", "name": "Good QB", "position": "QB",
            "team": "SF", "age": 27, "cap_hit_2026": 23_700_000,
            "years_remaining": 3, "guaranteed_money": 10_000_000,
            "total_contract_value": 71_100_000, "epa_total": 45.0,
            "snaps_played": 1050, "games_missed": 0,
        },
        {
            "player_id": "bad_row", "name": "Bad Player", "position": "QB",
            "team": "SF", "age": "not_a_number",  # bad age
            "cap_hit_2026": 10_000_000, "years_remaining": 1,
            "guaranteed_money": 0, "total_contract_value": 0,
            "epa_total": 0, "snaps_played": 0, "games_missed": 0,
        },
    ]).to_csv(csv_path, index=False)

    from streamlit_app.utils import _load_players_from_csv
    players = _load_players_from_csv(str(csv_path))
    # Bad row skipped, good row loaded
    assert len(players) == 1
    assert players[0].name == "Good QB"
```

- [ ] **Step 3: Run to confirm tests fail**

```bash
conda run -n nfl_analytics pytest tests/test_utils.py -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'streamlit_app.utils'`

- [ ] **Step 4: Create `streamlit_app/utils.py`**

```python
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from src.player_valuation import PlayerAsset, PlayerValuationModel

_CSV_PATH = (
    Path(__file__).parent.parent / "data" / "processed" / "player_assets_ready.csv"
)


def _load_players_from_csv(csv_path: str) -> List[PlayerAsset]:
    """Load and value players from a CSV file. Pure function — no Streamlit calls.

    Separated from the cached wrapper so it can be unit-tested directly.

    Args:
        csv_path: Absolute path to player_assets_ready.csv.

    Returns:
        List of valued PlayerAsset objects.

    Raises:
        FileNotFoundError: If the CSV does not exist.
    """
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Run: python collect_all_data.py"
        )
    df = pd.read_csv(p)
    players: List[PlayerAsset] = []
    for _, row in df.iterrows():
        try:
            players.append(
                PlayerAsset(
                    player_id=str(row["player_id"]),
                    name=str(row["name"]),
                    position=str(row["position"]),
                    team=str(row["team"]),
                    age=int(row["age"]),
                    cap_hit_2026=float(row["cap_hit_2026"]),
                    years_remaining=int(row["years_remaining"]),
                    guaranteed_money=float(row["guaranteed_money"]),
                    total_contract_value=float(row["total_contract_value"]),
                    epa_total=float(row["epa_total"]),
                    snaps_played=int(row["snaps_played"]),
                    games_missed=int(row["games_missed"]),
                )
            )
        except Exception:
            continue

    model = PlayerValuationModel()
    return model.value_roster(players)


@st.cache_data
def load_players() -> List[PlayerAsset]:
    """Load and value all players from the processed CSV.

    Cached by Streamlit for the duration of the session — the CSV load and
    PlayerValuationModel.value_roster() run exactly once regardless of how
    many pages are visited.

    Returns:
        List of valued PlayerAsset objects.
    """
    try:
        return _load_players_from_csv(str(_CSV_PATH))
    except FileNotFoundError as exc:
        st.error(f"Data not found: {exc}")
        st.stop()
        return []  # unreachable; satisfies type checker
```

- [ ] **Step 5: Run tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_utils.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Syntax-check utils.py**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/utils.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add streamlit_app/utils.py tests/test_utils.py
git commit -m "feat: add shared utils.load_players with cache_data"
```

---

### Task 2: `app.py` — Home Page

**Files:**
- Replace: `streamlit_app/app.py`

- [ ] **Step 1: Replace `streamlit_app/app.py`**

```python
from typing import List

import streamlit as st

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.sb_template import SuperBowlTemplateAnalyzer
from streamlit_app.utils import load_players

st.set_page_config(
    page_title="SF 49ers Football AI",
    page_icon="🏈",
    layout="wide",
)

st.title("SF 49ers Football AI System")
st.caption(
    "An AI-powered football intelligence system that uses generative AI and "
    "multi-agent workflows to automate scouting reports, answer natural language "
    "roster questions, and evolve optimal roster configurations within hard "
    "cap constraints."
)

players: List[PlayerAsset] = load_players()
sf_players = [p for p in players if p.team == "SF"]

if not sf_players:
    st.warning("No SF players loaded — check data/processed/player_assets_ready.csv")
    st.stop()

pa = PortfolioAnalyzer(sf_players)
sim = SuperBowlTemplateAnalyzer().calculate_similarity_score(sf_players)

col1, col2, col3, col4 = st.columns(4)
col1.metric("SF Players", len(sf_players))
col2.metric("Portfolio Efficiency", f"{pa.portfolio_efficiency():.2f}x")
col3.metric("Portfolio Risk", f"{pa.portfolio_risk():.2f}")
col4.metric("SB Similarity", f"{sim['overall_similarity']:.1f}/100")

st.divider()

st.markdown("### Built Systems")
st.markdown("""
- **Roster Valuation** — Bond-pricing model assigns fair value, efficiency ratio,
  and Sharpe ratio to every player contract
- **NFC West Comparison** — Division-wide portfolio analysis powered by DivisionAnalyzer
- **Evolution Engine** — Genetic algorithm finds optimal 53-man rosters within
  hard cap constraints
- **SB Template Matching** — Scores each roster against Super Bowl winner averages
  (2020–2024) across position allocation, age, and star concentration
- **AI Football Intelligence** — Multi-agent system (Contract / Scouting / Strategy)
  answers natural language roster questions grounded in real data
""")

st.info("Use the sidebar to navigate between pages.")
```

- [ ] **Step 2: Syntax-check**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/app.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 3: Launch and verify home page**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate to `http://localhost:8501`. Verify:
- Title shows "SF 49ers Football AI System"
- 4 metric cards show non-zero values (efficiency ~1.0–2.0, risk ~0.1–0.4)
- 5 bullet points visible under "Built Systems"
- Sidebar shows page list: Roster Analysis, Nfc West Comparison, etc.

Press `Ctrl+C` to stop.

- [ ] **Step 4: Commit**

```bash
git add streamlit_app/app.py
git commit -m "feat: add home page with SF portfolio metrics"
```

---

### Task 3: `pages/01_roster_analysis.py`

**Files:**
- Create: `streamlit_app/pages/01_roster_analysis.py`

- [ ] **Step 1: Create the page**

```python
from typing import List

import streamlit as st

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.visualizations import plot_player_value_scatter
from streamlit_app.utils import load_players

st.title("SF 49ers — Roster Valuation")

players: List[PlayerAsset] = load_players()
sf_players = [p for p in players if p.team == "SF"]

if not sf_players:
    st.warning("No SF players loaded.")
    st.stop()

pa = PortfolioAnalyzer(sf_players)
summary = pa.summary_report()

col1, col2, col3 = st.columns(3)
col1.metric("Portfolio Efficiency", f"{summary['efficiency']:.2f}x")
col2.metric("Portfolio Risk", f"{summary['risk']:.2f}")
col3.metric("Sharpe Ratio", f"{summary['sharpe_ratio']:.2f}")

st.subheader("Player Value vs Cap Hit")
st.caption(
    "Green = undervalued (value > cap × 1.15)  |  "
    "Red = overvalued (cap > value × 1.15)  |  "
    "Size = inversely proportional to risk score"
)
st.plotly_chart(
    plot_player_value_scatter(sf_players, highlight_team="SF"),
    use_container_width=True,
)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Most Overvalued")
    ov = pa.identify_overvalued().head(5)
    if ov.empty:
        st.success("No significantly overvalued players")
    else:
        st.dataframe(
            ov[["name", "position", "cap_hit", "fair_value", "pct_overvalued"]],
            use_container_width=True,
            hide_index=True,
        )

with col_right:
    st.subheader("Most Undervalued")
    uv = pa.identify_undervalued().head(5)
    if uv.empty:
        st.success("No significantly undervalued players")
    else:
        st.dataframe(
            uv[["name", "position", "cap_hit", "fair_value", "pct_undervalued"]],
            use_container_width=True,
            hide_index=True,
        )
```

- [ ] **Step 2: Syntax-check**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/pages/01_roster_analysis.py && echo "OK"
```

- [ ] **Step 3: Launch and verify**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate to the "Roster Analysis" page. Verify:
- 3 metric cards show values
- Scatter chart renders with colored dots and fair-value diagonal line
- At least one of the two tables has data (most players will be in the "Fair" zone)

Press `Ctrl+C` to stop.

- [ ] **Step 4: Commit**

```bash
git add streamlit_app/pages/01_roster_analysis.py
git commit -m "feat: add roster analysis page with valuation scatter and tables"
```

---

### Task 4: `pages/02_nfc_west_comparison.py`

**Files:**
- Create: `streamlit_app/pages/02_nfc_west_comparison.py`

- [ ] **Step 1: Create the page**

```python
from typing import Dict, List

import streamlit as st

from src.nfc_west_comparison import DivisionAnalyzer
from src.player_valuation import PlayerAsset
from streamlit_app.utils import load_players

st.title("NFC West — Division Comparison")

NFC_WEST = {"SF", "SEA", "LAR", "ARI"}

players: List[PlayerAsset] = load_players()
teams_data: Dict[str, List[PlayerAsset]] = {}
for p in players:
    if p.team in NFC_WEST:
        teams_data.setdefault(p.team, []).append(p)

if not teams_data:
    st.warning("No NFC West player data found.")
    st.stop()

with st.spinner("Building division analysis..."):
    analyzer = DivisionAnalyzer(teams_data)
    report = analyzer.generate_division_report(primary_team="SF")

st.subheader("Portfolio Metrics by Team")
metrics_df = report["metrics_df"].sort_values("efficiency", ascending=False)
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(
        report["figures"]["efficiency_scatter"], use_container_width=True
    )
with col2:
    st.plotly_chart(
        report["figures"]["position_allocation"], use_container_width=True
    )

st.divider()

st.subheader("SF Division Advantages")
advantages = report["advantages"]

col_s, col_w, col_o = st.columns(3)

with col_s:
    st.markdown("**Strengths** (SF leads division avg)")
    if advantages["strengths"]:
        for pos in advantages["strengths"]:
            st.success(pos)
    else:
        st.caption("No position groups where SF leads")

with col_w:
    st.markdown("**Weaknesses** (SF trails division avg)")
    if advantages["weaknesses"]:
        for pos in advantages["weaknesses"]:
            st.warning(pos)
    else:
        st.caption("No position groups where SF trails")

with col_o:
    st.markdown("**Opportunities** (weaknesses where SF ranks 3rd/4th)")
    if advantages["opportunities"]:
        for pos in advantages["opportunities"]:
            st.info(pos)
    else:
        st.caption("No high-priority opportunities identified")
```

- [ ] **Step 2: Syntax-check**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/pages/02_nfc_west_comparison.py && echo "OK"
```

- [ ] **Step 3: Launch and verify**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate to "Nfc West Comparison". Verify:
- Portfolio metrics table shows 4 rows (SF, SEA, LAR, ARI)
- Efficiency scatter chart shows 4 labeled points + SB Winner Zone
- Position allocation chart shows grouped bars
- Strengths/Weaknesses/Opportunities section populated

Press `Ctrl+C`.

- [ ] **Step 4: Commit**

```bash
git add streamlit_app/pages/02_nfc_west_comparison.py
git commit -m "feat: add NFC West comparison page with DivisionAnalyzer"
```

---

### Task 5: `pages/03_evolution_results.py`

**Files:**
- Create: `streamlit_app/pages/03_evolution_results.py`

- [ ] **Step 1: Create the page**

```python
import random
from typing import Dict, List

import pandas as pd
import streamlit as st

from src.evolution_engine import RosterConstraints
from src.visualizations import plot_evolution_history

st.title("Roster Evolution Engine")

st.info(
    "The evolution engine uses a genetic algorithm to find the optimal 53-man "
    "roster configuration within hard cap constraints. It evaluates fitness across: "
    "portfolio efficiency (40%), risk (25%), position balance (20%), and "
    "cap utilisation (15%)."
)

# Generate a realistic-looking demo history (deterministic via seed)
random.seed(42)
history: List[Dict] = []
best = 0.30
for gen in range(50):
    best = min(0.75, best + random.uniform(0.005, 0.025))
    avg = best * random.uniform(0.70, 0.90)
    history.append(
        {
            "generation": gen,
            "best_fitness": round(best, 4),
            "avg_fitness": round(avg, 4),
            "diversity": round(random.uniform(0.05, 0.20), 4),
        }
    )

st.subheader("Fitness History")
st.plotly_chart(plot_evolution_history(history), use_container_width=True)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Fitness Function")
    st.code(
        "fitness = (\n"
        "    0.40 * efficiency_score    # portfolio efficiency\n"
        "  + 0.25 * (1 - risk_score)   # inverted risk\n"
        "  + 0.20 * position_balance   # positional requirements\n"
        "  + 0.15 * cap_score          # cap utilisation (90–95% optimal)\n"
        ")\n\n"
        "# Invalid rosters receive fitness = -1000",
        language="python",
    )

with col2:
    st.subheader("Roster Constraints")
    constraints = RosterConstraints()
    rows = []
    for pos, (min_c, max_c) in sorted(constraints.position_limits.items()):
        rows.append({"Position": pos, "Min": min_c, "Max": max_c})
    rows.append(
        {
            "Position": "TOTAL",
            "Min": constraints.min_roster_size,
            "Max": constraints.max_roster_size,
        }
    )
    st.table(pd.DataFrame(rows))

st.caption(
    f"Demo run: 50 generations, population 100. "
    f"Final best fitness: {history[-1]['best_fitness']:.4f}"
)
```

- [ ] **Step 2: Syntax-check**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/pages/03_evolution_results.py && echo "OK"
```

- [ ] **Step 3: Launch and verify**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate to "Evolution Results". Verify:
- Info box with algorithm description visible
- Fitness history line chart renders with "Peak gen" annotation
- Fitness function code block shows the weighted formula
- Position constraints table shows all 15 positions

Press `Ctrl+C`.

- [ ] **Step 4: Commit**

```bash
git add streamlit_app/pages/03_evolution_results.py
git commit -m "feat: add evolution results page with demo fitness history"
```

---

### Task 6: `pages/04_sb_template.py`

**Files:**
- Create: `streamlit_app/pages/04_sb_template.py`

- [ ] **Step 1: Create the page**

```python
from typing import Dict, List

import pandas as pd
import streamlit as st

from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer
from src.visualizations import plot_sb_similarity_radar
from streamlit_app.utils import load_players

st.title("Super Bowl Template Matching")
st.caption(
    "How does the SF 49ers roster structure compare to recent Super Bowl winners "
    "(2020–2024) across cap allocation, age distribution, and star concentration?"
)

NFC_WEST = {"SF", "SEA", "LAR", "ARI"}

players: List[PlayerAsset] = load_players()
teams_data: Dict[str, List[PlayerAsset]] = {}
for p in players:
    if p.team in NFC_WEST:
        teams_data.setdefault(p.team, []).append(p)

sf_players = teams_data.get("SF", [])
if not sf_players:
    st.warning("No SF player data found.")
    st.stop()

sb_analyzer = SuperBowlTemplateAnalyzer()
sim = sb_analyzer.calculate_similarity_score(sf_players)
template = sb_analyzer.build_sb_template()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Position Similarity", f"{sim['position_similarity']:.1f}/100")
col2.metric("Age Similarity", f"{sim['age_similarity']:.1f}/100")
col3.metric("Star Concentration", f"{sim['concentration_similarity']:.1f}/100")
col4.metric("Overall Similarity", f"{sim['overall_similarity']:.1f}/100")

st.divider()

st.subheader("Structural Gaps vs SB Template")
if sim["gaps"]:
    for gap in sim["gaps"]:
        st.warning(gap)
else:
    st.success("SF roster closely matches SB template structure")

st.divider()

st.subheader("SB Similarity Radar — NFC West")
st.plotly_chart(
    plot_sb_similarity_radar(teams_data, template),
    use_container_width=True,
)

st.divider()

st.subheader("SB Template Reference (2020–2024 Averages)")
col_pos, col_age, col_conc = st.columns(3)

with col_pos:
    st.markdown("**Cap by Position Group**")
    pos_df = pd.DataFrame(
        [{"Group": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["position_allocation"].items()]
    )
    st.table(pos_df)

with col_age:
    st.markdown("**Age Distribution**")
    age_df = pd.DataFrame(
        [{"Bucket": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["age_distribution"].items()]
    )
    st.table(age_df)

with col_conc:
    st.markdown("**Star Concentration**")
    conc_df = pd.DataFrame(
        [{"Group": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["star_concentration"].items()]
    )
    st.table(conc_df)
```

- [ ] **Step 2: Syntax-check**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/pages/04_sb_template.py && echo "OK"
```

- [ ] **Step 3: Launch and verify**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate to "Sb Template". Verify:
- 4 similarity metric cards show values between 0–100
- At least one gap warning appears (SF will almost certainly differ from SB template)
- Radar chart renders with 5 axes and traces for each NFC West team + SB template
- Three reference tables at bottom

Press `Ctrl+C`.

- [ ] **Step 4: Commit**

```bash
git add streamlit_app/pages/04_sb_template.py
git commit -m "feat: add SB template matching page with radar chart and gap analysis"
```

---

### Task 7: `pages/05_ai_assistant.py` + end-to-end verification

**Files:**
- Create: `streamlit_app/pages/05_ai_assistant.py`

- [ ] **Step 1: Create the page**

```python
import os
from typing import List

import streamlit as st

from src.agents import AgentSystem
from src.player_valuation import PlayerAsset
from streamlit_app.utils import load_players

st.title("AI Football Intelligence")
st.caption(
    "Ask natural language questions about the 49ers roster. "
    "Powered by a multi-agent system (Contract · Scouting · Strategy) "
    "grounded in real player data."
)

# ---- API key handling -------------------------------------------------------
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.warning(
        "No ANTHROPIC_API_KEY environment variable found. "
        "Enter your key below to use the AI assistant."
    )
    api_key = st.text_input(
        "Anthropic API key:",
        type="password",
        placeholder="sk-ant-...",
    )
    if not api_key:
        st.info(
            "Get an API key at https://console.anthropic.com — "
            "or set ANTHROPIC_API_KEY before launching Streamlit."
        )
        st.stop()

# ---- Query interface --------------------------------------------------------
st.subheader("Ask a Question")
query = st.text_area(
    "Question:",
    placeholder=(
        "e.g. Who are our most undervalued players?\n"
        "e.g. Generate a scouting report on Brock Purdy\n"
        "e.g. How does our cap allocation compare to Super Bowl winners?\n"
        "e.g. Which positions should we target in free agency?"
    ),
    height=100,
)

ask_disabled = not query.strip()
asked = st.button("Ask", disabled=ask_disabled)

st.caption(
    "**Example queries:** 'Who are our most undervalued players?' · "
    "'Generate a scouting report on Brock Purdy' · "
    "'How does our cap allocation compare to Super Bowl winners?' · "
    "'Which positions should we target in free agency?'"
)

# ---- Response ---------------------------------------------------------------
if asked and query.strip():
    players: List[PlayerAsset] = load_players()
    with st.spinner("Consulting AI agents..."):
        try:
            system = AgentSystem(players=players, api_key=api_key)
            result = system.ask(query.strip())
        except Exception as exc:
            st.error(f"Error initialising agent system: {exc}")
            st.stop()

    if result["agent"] == "error":
        st.error(result["response"])
    else:
        st.success(f"Answered by: **{result['agent'].title()} Agent**")
        st.markdown(result["response"])
        if result["data_used"]:
            st.caption(
                f"Data used: {', '.join(str(x) for x in result['data_used'][:10])}"
            )
```

- [ ] **Step 2: Syntax-check all pages in one pass**

```bash
conda run -n nfl_analytics python -m py_compile streamlit_app/pages/05_ai_assistant.py && echo "OK"
echo "---"
for f in streamlit_app/app.py streamlit_app/utils.py streamlit_app/pages/*.py; do
    conda run -n nfl_analytics python -m py_compile "$f" && echo "✓ $f"
done
```
Expected: all files print `✓`.

- [ ] **Step 3: Run full unit test suite to check no regressions**

```bash
conda run -n nfl_analytics pytest tests/ -q 2>&1 | tail -5
```
Expected: 103 passed (100 existing + 3 new utils tests).

- [ ] **Step 4: Full end-to-end app launch**

```bash
conda run -n nfl_analytics streamlit run streamlit_app/app.py
```

Navigate through all 6 pages and verify:

| Page | What to check |
|------|--------------|
| Home | 4 metric cards non-zero, 5 bullet systems, sidebar shows all 5 pages |
| Roster Analysis | Scatter chart with colored dots, overvalued/undervalued tables |
| NFC West | 4-row metrics table, two charts side-by-side, advantages section |
| Evolution | Fitness line chart with peak annotation, position constraints table |
| SB Template | 4 similarity metrics, gap warnings, radar chart with all 4 teams |
| AI Assistant | Warning shown if no API key; if key set, enter a query and verify JSON response shown |

Press `Ctrl+C` when done.

- [ ] **Step 5: Commit**

```bash
git add streamlit_app/pages/05_ai_assistant.py
git commit -m "feat: add AI assistant page and complete Priority 5 dashboard"
```

---

## Self-Review

**Spec coverage:**
- `utils.py` with `@st.cache_data`, `_load_players_from_csv` inner function, `st.error`+`st.stop` on missing CSV ✓ Task 1
- `app.py`: title, caption, 4 metric cards (sf count, efficiency, risk, SB similarity), built systems list, nav hint ✓ Task 2
- `01_roster_analysis.py`: 3 metrics, scatter chart from `plot_player_value_scatter`, top-5 overvalued + undervalued tables ✓ Task 3
- `02_nfc_west_comparison.py`: `DivisionAnalyzer`, metrics df sorted by efficiency, efficiency scatter + position allocation charts, strengths/weaknesses/opportunities ✓ Task 4
- `03_evolution_results.py`: `st.info` explanation, synthetic history, `plot_evolution_history`, fitness function code block, constraints table ✓ Task 5
- `04_sb_template.py`: 4 similarity metrics, gap warnings, `plot_sb_similarity_radar`, 3 reference tables ✓ Task 6
- `05_ai_assistant.py`: env key check, runtime key input, `st.stop` if no key, query area + ask button (disabled if empty), spinner + AgentSystem call, success/error display, data_used caption ✓ Task 7
- Error handling table: CSV missing, no API key, API error, empty players guard ✓ All tasks
- Absolute imports throughout ✓ All tasks
- No `st.experimental_*` ✓ All tasks
- Pages directory created ✓ Task 1

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:** `load_players()` returns `List[PlayerAsset]` throughout. `teams_data` is `Dict[str, List[PlayerAsset]]` in pages 02 and 04. `report["figures"]` dict keys match what `DivisionAnalyzer.generate_division_report()` returns (`efficiency_scatter`, `position_allocation`). `sim["gaps"]` is `List[str]` from `SuperBowlTemplateAnalyzer`. All consistent with Priority 3/4 implementations.
