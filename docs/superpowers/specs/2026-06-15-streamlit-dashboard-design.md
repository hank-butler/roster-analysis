# Streamlit Dashboard Design
**Date:** 2026-06-15
**Priority:** 5 — Dashboard
**Goal:** A clean, functional 6-page Streamlit app that demonstrates all five built systems (valuation model, division analysis, evolution engine, SB template matching, AI agent) to a 49ers front-office audience.

---

## Architecture

```
streamlit_app/
├── app.py                       # Home page: project overview + quick portfolio metrics
├── utils.py                     # @st.cache_data data loading, shared by all pages
└── pages/
    ├── 01_roster_analysis.py    # Player value scatter + overvalued/undervalued tables
    ├── 02_nfc_west_comparison.py # DivisionAnalyzer charts + division rankings
    ├── 03_evolution_results.py  # Static demo evolution fitness history
    ├── 04_sb_template.py        # SB similarity radar + gap analysis for SF
    └── 05_ai_assistant.py       # AgentSystem chat interface
```

**Data loading:** `utils.py` exports one function annotated with `@st.cache_data`. All pages import and call `load_players()`. Streamlit caches across the session so the CSV + `value_roster()` runs once regardless of which page is visited first.

**No custom CSS or theming.** Default Streamlit styling. Focus on correctness and clarity, not presentation polish.

---

## `streamlit_app/utils.py`

```python
@st.cache_data
def load_players() -> List[PlayerAsset]:
    """Load player_assets_ready.csv, construct PlayerAsset objects, value via PlayerValuationModel."""
```

- Reads `data/processed/player_assets_ready.csv`
- Constructs `PlayerAsset` objects row by row (same logic as `agent_system._load_players_from_csv`)
- Calls `PlayerValuationModel().value_roster(players)`
- Returns valued `List[PlayerAsset]`
- If CSV not found: `st.error("Data not found. Run: python collect_all_data.py")` then `st.stop()`

---

## `streamlit_app/app.py` — Home Page

**Content (top to bottom):**

1. `st.title("SF 49ers Football AI System")`
2. `st.caption` with positioning statement: *"An AI-powered football intelligence system that uses generative AI and multi-agent workflows to automate scouting reports, answer natural language roster questions, and evolve optimal roster configurations within hard cap constraints."*
3. Four `st.metric` cards in a `st.columns(4)` row (computed from SF players only):
   - **Players loaded** — total count from `load_players()` filtered to SF
   - **Portfolio efficiency** — `PortfolioAnalyzer(sf_players).portfolio_efficiency()`, formatted as `1.23x`
   - **Portfolio risk** — `PortfolioAnalyzer(sf_players).portfolio_risk()`, formatted as `0.21`
   - **SB similarity** — `SuperBowlTemplateAnalyzer().calculate_similarity_score(sf_players)["overall_similarity"]`, formatted as `67.4/100`
4. `st.markdown` section: "**Built Systems**" — bullet list of the 5 modules with one-line descriptions
5. `st.info("Use the sidebar to navigate between pages.")`

---

## `streamlit_app/pages/01_roster_analysis.py` — Roster Analysis

**Title:** `st.title("SF 49ers — Roster Valuation")`

**Content:**

1. Three `st.metric` cards in a row: portfolio efficiency, portfolio risk, Sharpe ratio (from `PortfolioAnalyzer`)
2. `st.subheader("Player Value vs Cap Hit")`
   - `st.plotly_chart(plot_player_value_scatter(sf_players, highlight_team="SF"), use_container_width=True)`
3. Two columns side by side:
   - Left: `st.subheader("Most Overvalued")` → `st.dataframe` of top 5 from `PortfolioAnalyzer(sf_players).identify_overvalued()` — columns: name, position, cap_hit, fair_value, pct_overvalued
   - Right: `st.subheader("Most Undervalued")` → `st.dataframe` of top 5 from `identify_undervalued()` — columns: name, position, cap_hit, fair_value, pct_undervalued

Data: SF players only, filtered from `load_players()`.

---

## `streamlit_app/pages/02_nfc_west_comparison.py` — NFC West Comparison

**Title:** `st.title("NFC West — Division Comparison")`

**Content:**

1. Build `teams_data` by splitting `load_players()` by team — explicitly filter to `{"SF", "SEA", "LAR", "ARI"}` only (discard any other teams that might appear in the CSV)
2. `analyzer = DivisionAnalyzer(teams_data)` — called once, results reused
3. `report = analyzer.generate_division_report(primary_team="SF")` — all figures pre-built
4. `st.subheader("Portfolio Metrics")` → `st.dataframe(report["metrics_df"])` sorted by efficiency
5. Two columns:
   - Left: `st.plotly_chart(report["figures"]["efficiency_scatter"], use_container_width=True)`
   - Right: `st.plotly_chart(report["figures"]["position_allocation"], use_container_width=True)`
6. `st.subheader("SF Division Advantages")`
   - Strengths as `st.success` badges
   - Weaknesses as `st.warning` badges
   - Opportunities as `st.info` badges

Note: `DivisionAnalyzer` re-values all players internally at init — this is a known double-valuation but acceptable for a demo.

---

## `streamlit_app/pages/03_evolution_results.py` — Evolution Results

**Title:** `st.title("Roster Evolution Engine")`

**Content:**

1. `st.info` box explaining what the EvolutionEngine does:
   - *"The evolution engine uses a genetic algorithm to find the optimal 53-man roster configuration within hard cap constraints. It evaluates fitness across: portfolio efficiency (40%), risk (25%), position balance (20%), and cap utilisation (15%)."*
2. Synthetic demo history generated inline (no EvolutionEngine call):
   ```python
   import random, math
   random.seed(42)
   history = []
   best = 0.3
   for gen in range(50):
       best = min(0.75, best + random.uniform(0.005, 0.025))
       avg = best * random.uniform(0.7, 0.9)
       history.append({"generation": gen, "best_fitness": round(best, 4),
                       "avg_fitness": round(avg, 4), "diversity": round(random.uniform(0.05, 0.2), 4)})
   ```
3. `st.plotly_chart(plot_evolution_history(history), use_container_width=True)`
4. `st.subheader("Fitness Function")` → `st.code` block showing the weights
5. `st.subheader("Roster Constraints")` → `st.table` of position limits from `RosterConstraints()`

---

## `streamlit_app/pages/04_sb_template.py` — SB Template Matching

**Title:** `st.title("Super Bowl Template Matching")`

**Content:**

1. Build `teams_data` with all 4 NFC West teams (same as page 02)
2. `sb_analyzer = SuperBowlTemplateAnalyzer()`
3. SF similarity: `sim = sb_analyzer.calculate_similarity_score(sf_players)`
4. Four `st.metric` cards in a row: position similarity, age similarity, concentration similarity, overall similarity (all `X.X/100`)
5. `st.subheader("Structural Gaps vs SB Template")`
   - For each gap in `sim["gaps"]`: `st.warning(gap)`
   - If no gaps: `st.success("SF roster closely matches SB template structure")`
6. `st.subheader("SB Similarity Radar — NFC West")`
   - `st.plotly_chart(plot_sb_similarity_radar(teams_data, sb_analyzer.build_sb_template()), use_container_width=True)`
7. `st.subheader("SB Template Reference")`
   - `st.table` showing the hardcoded SB winner averages (position %, age %, star concentration)

---

## `streamlit_app/pages/05_ai_assistant.py` — AI Assistant

**Title:** `st.title("AI Football Intelligence")`

**Content:**

1. **API key handling:**
   ```
   key = os.getenv("ANTHROPIC_API_KEY")
   if not key:
       st.warning("No ANTHROPIC_API_KEY found in environment.")
       key = st.text_input("Enter your Anthropic API key:", type="password")
   ```
   If still no key after input: `st.stop()`

2. **Query interface:**
   - `st.text_area("Ask a question about the 49ers roster:")` with placeholder examples
   - `st.button("Ask")` — disabled if query is empty

3. **On submit:**
   ```python
   with st.spinner("Consulting AI agents..."):
       system = AgentSystem(players=load_players(), api_key=key)
       result = system.ask(query)
   ```
   Display:
   - `st.success(f"Answered by: {result['agent'].title()} Agent")`
   - `st.markdown(result["response"])`
   - `st.caption(f"Data used: {', '.join(result['data_used'][:10])}")`

4. **Example queries** shown below the input (as `st.caption` text):
   - "Who are our most undervalued players?"
   - "Generate a scouting report on Brock Purdy"
   - "How does our cap allocation compare to Super Bowl winners?"
   - "Which positions should we target in free agency?"

---

## Error Handling

| Situation | Behaviour |
|---|---|
| `player_assets_ready.csv` not found | `utils.py`: `st.error(...)` + `st.stop()` |
| `ANTHROPIC_API_KEY` not set | Page 5: show text_input for runtime key entry |
| API error during agent call | Show `st.error(result["response"])` — agent returns error dict, never raises |
| `DivisionAnalyzer` fails | `generate_division_report` has internal try/except; page falls back gracefully |
| Empty player list after loading | Each page shows `st.warning("No players loaded")` guard before rendering |

---

## Key Constraints

- All imports absolute from project root (`from src.player_valuation import ...`)
- No test files for Streamlit pages — UI correctness is verified by running the app
- `utils.py` `load_players()` must handle the same CSV path robustness as `agent_system.py` (use `Path(__file__)` for absolute path resolution)
- No `st.experimental_*` APIs — use stable Streamlit APIs only
- Each page is self-contained and works even if visited first (no mandatory home page visit)
- `streamlit run streamlit_app/app.py` launches the app from the project root
