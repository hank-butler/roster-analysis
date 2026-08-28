# CLAUDE.md - NFL Football AI System
## Project Context for Claude Code

---

## 🎯 Project Overview

This is a **Football AI System** built as a portfolio project targeting a
**Denver Broncos Analytics Engineer** position (business-side analytics).
Three capabilities share the headline: the multi-source data pipeline
(ETL, fuzzy merging, validation), the predictive modeling layer (valuation,
risk scoring, efficiency ratios — the same machinery as lead scoring or
fan-propensity models), and the Claude-powered multi-agent layer (agentic
workflows and LLM applications). Roster construction is the demo domain,
framed honestly as such: the scoring, segmentation, and optimization
patterns transfer to lead scoring, demand forecasting, and fan-propensity
modeling.

**Core Thesis:** Treat NFL roster construction as a portfolio optimization
problem under a hard salary cap constraint. Each player is a financial asset
with expected returns (performance), risk (injury/age), and cost (cap hit).
Use evolutionary algorithms to find optimal roster configurations, and wrap
everything in a multi-agent AI layer for natural language interaction.

**Target Team:** Denver Broncos  
**Division Comparison:** AFC West (Broncos, Chiefs, Chargers, Raiders)  
**Super Bowl Template:** Chiefs (2020, 2023, 2024), Buccaneers (2021),
Rams (2022), Eagles (2025)

---

## 🏗️ Architecture

```
nfl_roster_optimizer/
├── CLAUDE.md                        # This file
├── README.md                        # Public-facing documentation
├── requirements.txt                 # Python dependencies
├── collect_all_data.py              # Master data collection script
├── .gitignore
├── LICENSE
│
├── data/
│   ├── raw/
│   │   ├── performance/             # nflfastR data
│   │   │   ├── pbp_2023_2025.parquet
│   │   │   ├── player_stats_2023_2025.csv
│   │   │   ├── rosters_2023_2025.csv
│   │   │   └── injuries_2023_2025.csv
│   │   ├── contracts/               # OverTheCap scraped data
│   │   │   ├── den_2026.csv
│   │   │   ├── lac_2026.csv
│   │   │   ├── lv_2026.csv
│   │   │   └── sb_winners/          # incl. KC (also an AFC West rival)
│   │   └── super_bowl_winners/      # Historical SB roster data
│   └── processed/                   # Merged, model-ready data
│       ├── afc_west_rosters.csv
│       ├── player_assets_ready.csv
│       ├── evolution_results.json
│       └── sb_winners_combined.csv
│
├── src/
│   ├── __init__.py
│   ├── player_valuation.py          # ✅ COMPLETE - Bond pricing model
│   ├── evolution_engine.py          # ✅ COMPLETE - Genetic algorithm
│   ├── portfolio_optimizer.py       # ✅ COMPLETE - Efficient frontier
│   ├── sb_template.py               # ✅ COMPLETE - SB winner matching
│   ├── afc_west_comparison.py       # ✅ COMPLETE - Division comparison framework
│   ├── visualizations.py            # ✅ COMPLETE - Plotly charts
│   │
│   ├── data_collection/
│   │   ├── __init__.py
│   │   ├── nflfastr_collection.py   # ✅ COMPLETE - Performance data
│   │   ├── overthecap_scraper.py    # ✅ COMPLETE - Contract scraping
│   │   ├── roster_builder.py        # ✅ COMPLETE - Merges data sources
│   │   └── data_processor.py        # ✅ COMPLETE - Feature engineering
│   │
│   └── agents/                      # ✅ COMPLETE - Multi-agent AI layer
│       ├── __init__.py
│       ├── coordinator_agent.py     # Orchestrates other agents
│       ├── contract_agent.py        # Cap/contract analysis
│       ├── scouting_agent.py        # Player scouting reports
│       ├── strategy_agent.py        # Game strategy insights
│       └── agent_system.py          # Entry point for agent system
│
├── streamlit_app/
│   ├── app.py                       # ✅ COMPLETE - Main dashboard
│   ├── utils.py
│   └── pages/
│       ├── 01_roster_analysis.py
│       ├── 02_afc_west_comparison.py
│       ├── 03_evolution_results.py
│       ├── 04_sb_template.py
│       └── 05_ai_assistant.py
│
├── docs/
│   ├── model_insights.md
│   └── broncos_2026_cap_context.md  # Sourced cap research (OTC, team site)
│
└── tests/                           # ✅ Full pytest suite (see Testing)
```

---

## ✅ Completed Modules

### `src/player_valuation.py`
Core valuation model. Three main classes:

- **`PlayerAsset`** - Dataclass representing a player as a financial asset
- **`PlayerValuationModel`** - Calculates fair value, risk, efficiency, Sharpe ratio
- **`PortfolioAnalyzer`** - Analyzes full roster as asset portfolio

Key methods:
```python
model = PlayerValuationModel()
player = model.value_player(player_asset)      # Values single player
roster = model.value_roster(list_of_assets)    # Values entire roster
analyzer = PortfolioAnalyzer(valued_roster)
summary = analyzer.summary_report()            # Full portfolio metrics
overvalued = analyzer.identify_overvalued()    # Players cap > fair value
undervalued = analyzer.identify_undervalued()  # Bargain players
```

### `src/evolution_engine.py`
Genetic algorithm for roster optimization. Three main classes:

- **`RosterConstraints`** - NFL roster rules (53 players, position limits, cap)
- **`Chromosome`** - One possible roster configuration
- **`EvolutionEngine`** - Runs the genetic algorithm

Key methods:
```python
engine = EvolutionEngine(current_roster, available_players, constraints, model)
best_roster, history = engine.evolve()    # Returns optimal roster + history
```

Fitness function weights:
- Portfolio efficiency: 40%
- Portfolio risk (inverted): 25%
- Position balance: 20%
- Cap utilization (90-95% optimal): 15%

### `src/data_collection/nflfastr_collection.py`
Collects performance data via `nfl_data_py`:
```python
collector = NFLDataCollector()
data = collector.collect_all([2023, 2024, 2025])
# Returns dict: {pbp, stats, rosters, injuries}
```

---

## 🔧 Build Log (historical — statuses reflect current codebase)

### Priority 1: Fix Broken Things
- [x] Fix imports in `evolution_engine.py` (bare → relative)
- [x] Fix imports in `test_evolution.py` and `test_evaluation.py`
- [x] Remove undefined `main()` call in `player_valuation.py`
- [x] Create `src/data_collection/__init__.py`
- [x] Fix f-string formatting bug in the nflfastR collector

### Priority 2: Complete Data Collection
- [x] Finish `overthecap_scraper.py` with Broncos/AFC West teams
- [x] Build `roster_builder.py` to merge performance + contract data
- [x] Build `data_processor.py` for feature engineering
- [x] Create `collect_all_data.py` master script

### Priority 3: Analysis Modules
- [x] `sb_template.py` - Super Bowl winner template matching
- [x] `afc_west_comparison.py` - Division comparison framework
- [x] `portfolio_optimizer.py` - Efficient frontier analysis
- [x] `visualizations.py` - Plotly charts

### Priority 4: AI Agent Layer (Critical for Broncos Role)
- [x] `agents/coordinator_agent.py` - Orchestrates specialist agents
- [x] `agents/contract_agent.py` - Natural language cap analysis
- [x] `agents/scouting_agent.py` - Generates scouting reports
- [x] `agents/strategy_agent.py` - Game strategy insights

### Priority 5: Dashboard
- [x] `streamlit_app/app.py` - Main Streamlit dashboard
- [x] Individual page modules

---

## 🧠 Key Design Decisions

### Player Valuation (Bond Pricing Analogy)
| Bond Concept | NFL Equivalent |
|---|---|
| Face Value | Total contract value |
| Coupon Payment | Annual cap hit |
| Maturity Date | Contract expiration |
| Yield | Performance ROI |
| Credit Risk | Injury/age risk |
| Duration | Contract sensitivity |
| Callable | Team can cut player |

### Risk Score Components
- Injury risk (40%): `games_missed / 51` (3 seasons × 17 games)
- Age risk (40%): Distance from position peak age
- Position risk (20%): Positional longevity (RB riskier than QB)

### Fitness Function (Evolution)
```
fitness = 0.40 * efficiency_score
        + 0.25 * (1 - risk_score)
        + 0.20 * position_balance
        + 0.15 * cap_utilization_score
```
Invalid rosters (wrong size, over cap, missing positions) get fitness = -1000.

### Position Peak Ages
```python
QB: 28, WR: 26, RB: 25, TE: 27
OT: 28, OG: 28, C: 29
EDGE: 27, DL: 27, LB: 27
CB: 27, S: 27
K/P/LS: 30
```

---

## 🌐 Data Sources

| Source | What | How |
|---|---|---|
| `nfl_data_py` | Performance data (EPA, stats, rosters, injuries) | Python package |
| `overthecap.com` | Contract data (cap hits, guarantees, dead cap) | Web scraping |
| `pro-football-reference.com` | Historical stats if needed | Web scraping |

### OverTheCap Team Slugs
```python
TEAM_SLUGS = {
    # AFC West (Primary)
    "DEN": "denver-broncos",
    "LAC": "los-angeles-chargers",
    "LV":  "las-vegas-raiders",
    "KC":  "kansas-city-chiefs",     # dual role: rival + SB template
    # Super Bowl Winners (Template Matching)
    "TB":  "tampa-bay-buccaneers",
    "PHI": "philadelphia-eagles",
    # Legacy entries from the original NFC West build (kept for reference)
    "SF":  "san-francisco-49ers",
    "SEA": "seattle-seahawks",
    "LAR": "los-angeles-rams",
    "ARI": "arizona-cardinals",
}
```

### Broncos 2026 Cap Context
All figures sourced in `docs/broncos_2026_cap_context.md` (OTC live fetch,
2026-08-27) — do not use numbers that aren't in that file.
- ~$37.3M in cap space
- ~$3.5M in dead money
- Top 2026 cap hits: McGlinchey ($23.8M), Zach Allen ($16.5M),
  D.J. Jones ($14.6M), Engram ($14.1M), Sutton ($14.0M),
  Hufanga ($13.5M), Surtain ($12.7M)
- QB: Bo Nix ($5.1M 2026 cap hit per `data/raw/contracts/den_2026.csv`)
- Needs: ILB (Dre Greenlaw was released — he is NOT on the roster),
  TE, RB depth
- Acquired by trade: WR Jaylen Waddle (from Miami)
- Key re-signings: Dobbins (RB), Singleton (ILB), Strnad (ILB),
  Trautman (TE), among others

---

## 🤖 Multi-Agent System Design

Uses Claude API (`claude-sonnet-4-6`) with specialized agents:

```
User Query
    ↓
Coordinator Agent
    ├── Contract Agent    → Cap analysis, valuations
    ├── Scouting Agent    → Player reports grounded in data
    └── Strategy Agent    → Play-calling, matchup analysis
    ↓
Synthesized Response
```

Example queries the system should handle:
- "Who are our most undervalued players?"
- "Generate a scouting report on Courtland Sutton vs the Chiefs"
- "How does our cap situation compare to the Chargers?"
- "What positions should we target in free agency?"
- "Which players should we consider cutting or trading?"

Agent API calls use `claude-sonnet-4-6` with data injected as context.
Never hallucinate player stats - always ground in real data from data pipeline.

---

## 💻 Environment & Conventions

### Environment
- **OS:** Pop!_OS (Linux) on System76
- **Python:** 3.11 via conda (`nfl_analytics` environment)
- **Package manager:** conda + pip
- **Editor:** Terminal-centric workflow

### Activate Environment
```bash
conda activate nfl_analytics
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Running Scripts
```bash
# From project root
python collect_all_data.py           # Full data pipeline
pytest tests/ -v                     # Run the test suite
streamlit run streamlit_app/app.py   # Launch dashboard
```

### Code Style
- **Language:** Python 3.11
- **Docstrings:** Google style preferred
- **Type hints:** Always include
- **Line length:** 88 chars (Black default)
- **Imports:** Absolute from project root (e.g., `from src.player_valuation import ...`)
- **Logging:** Use `logging` module, not `print()` in production code
- **Constants:** UPPER_SNAKE_CASE at module level

### Key Conventions
1. **Always use absolute imports** from project root - never bare imports
2. **PlayerAsset is a dataclass** - don't add methods, use PlayerValuationModel
3. **Chromosome is mutable** - always `.clone()` before modifying
4. **Raw data files go in `data/raw/`** — never commit them to git. Processed demo files in `data/processed/` are intentionally tracked.
5. **Tests go in `tests/`** - not in `src/`
6. **Save all scraped data** before processing - raw data is valuable
7. **Rate limit scrapers** - 2 second minimum delay between OTC requests

---

## 🚫 Known Issues & Gotchas

1. **Bare imports will break** if running from project root. Always use
   `from src.module import ...`

2. **Evolution can get stuck** if available_players pool doesn't have
   enough players at each position to fill constraints. Ensure pool has
   10+ players per position.

3. **OverTheCap HTML structure** may change. If scraper breaks, inspect
   the page and update CSS selectors in `overthecap_scraper.py`.

4. **nfl_data_py is slow** on first run (downloads large parquet files).
   Data is cached after first download - subsequent runs are fast.

5. **EPA for non-skill positions** (OL, DL, LB) is hard to calculate
   directly from play-by-play. Use proxy metrics or positional WAR
   estimates until tracking data is available.

6. **Fitness of -1000** means invalid roster (usually wrong roster size
   or position count). Check `Chromosome.is_valid()` constraints.

---

## 📊 Key Metrics Reference

### Player-Level
| Metric | Description | Good Value |
|---|---|---|
| `efficiency_ratio` | Expected value / cap hit | > 1.0 |
| `risk_score` | Weighted risk 0-1 | < 0.3 |
| `sharpe_ratio` | Risk-adjusted return | > 1.0 |
| `fair_value` | What player should cost | Compare to cap_hit |

### Portfolio-Level
| Metric | Description | Target |
|---|---|---|
| `portfolio_efficiency` | Total value / total cost | > 1.15 |
| `portfolio_risk` | Weighted avg risk | < 0.25 |
| `portfolio_sharpe` | Portfolio Sharpe ratio | > 1.0 |

### Evolution
| Parameter | Current Value | Notes |
|---|---|---|
| `population_size` | 100 | Reduce to 20-50 for testing |
| `generations` | 100 | Reduce to 10-20 for testing |
| `mutation_rate` | 0.15 | 15% chance of mutation |
| `crossover_rate` | 0.80 | 80% chance of crossover |
| `elitism_count` | 5 | Top 5 always survive |

---

## 🎯 Application Context

This project is a portfolio piece for a **Denver Broncos Analytics
Engineer** position (business-side analytics: ticketing, marketing,
sponsorship, fan engagement). The posting emphasizes SQL/Python, ETL and
data warehousing, predictive modeling, lead scoring and segmentation,
agentic workflows / LLM applications (Claude is named in preferred
qualifications), dashboards, and storytelling. How this project maps:

1. **ETL & data integration** - Multi-source pipeline (nflfastR +
   OverTheCap) with fuzzy merging, checkpointing, and validation
2. **Predictive / scoring models** - Valuation, risk, and efficiency
   scoring: the same machinery as lead scoring and fan-propensity models
3. **Agentic workflows & LLM applications** - Claude API multi-agent
   system with a coordinator routing to grounded specialists
4. **Dashboards & storytelling** - Streamlit app that turns portfolio
   math into narratives a non-technical stakeholder can act on
5. **Honest framing** - Roster construction is the demo domain; the
   project does NOT claim Snowflake/dbt/Power BI experience it doesn't
   demonstrate

### Positioning Statement
> "An end-to-end analytics system — multi-source ETL pipeline, predictive
> scoring models, and a Claude-powered multi-agent layer — demonstrated on
> NFL roster construction. The same scoring, segmentation, and
> constrained-optimization machinery transfers directly to lead scoring,
> demand forecasting, and fan-propensity modeling."

---

## 📝 TODO Checklist (historical — statuses reflect current codebase)

### Immediate Fixes
- [x] Fix bare imports → absolute imports everywhere
- [x] Remove undefined `main()` in `player_valuation.py`
- [x] Create `src/data_collection/__init__.py`
- [x] Fix f-string bug in the nflfastR collector
- [x] Move test files from `src/` to `tests/`

### Data Collection
- [x] Complete `overthecap_scraper.py` for Broncos/AFC West
- [x] Build `roster_builder.py`
- [x] Create `collect_all_data.py`
- [x] Run full data collection pipeline
- [x] Validate merged data quality

### Core Models
- [x] `sb_template.py` - SB winner similarity scoring
- [x] `afc_west_comparison.py` - Division comparison
- [x] `visualizations.py` - Plotly charts

### AI Layer
- [x] Claude API integration setup
- [x] Coordinator agent
- [x] Contract agent
- [x] Scouting report generator
- [x] Strategy agent

### Dashboard
- [x] Streamlit app structure
- [x] Roster analysis page
- [x] AFC West comparison page
- [x] Evolution results page
- [x] SB template page
- [x] AI assistant page

### Polish
- [x] README.md
- [x] Docstrings on all public methods
- [x] Unit tests for core modules
- [ ] Demo video recording