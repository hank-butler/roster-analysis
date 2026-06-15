# CLAUDE.md - NFL Football AI System
## Project Context for Claude Code

---

## 🎯 Project Overview

This is a **Football AI System** built as a portfolio project targeting the
**San Francisco 49ers Football AI Fellow** position. The system combines
real NFL data, bond-pricing valuation models, portfolio optimization theory,
and generative AI to support front office decision-making across Player
Personnel, Coaching, and Scouting.

**Core Thesis:** Treat NFL roster construction as a portfolio optimization
problem under a hard salary cap constraint. Each player is a financial asset
with expected returns (performance), risk (injury/age), and cost (cap hit).
Use evolutionary algorithms to find optimal roster configurations, and wrap
everything in a multi-agent AI layer for natural language interaction.

**Target Team:** San Francisco 49ers  
**Division Comparison:** NFC West (49ers, Seahawks, Rams, Cardinals)  
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
│   │   │   ├── sf_2026.csv
│   │   │   ├── sea_2026.csv
│   │   │   ├── lar_2026.csv
│   │   │   ├── ari_2026.csv
│   │   │   └── sb_winners/
│   │   └── super_bowl_winners/      # Historical SB roster data
│   └── processed/                   # Merged, model-ready data
│       ├── sf_full_roster.csv
│       ├── nfc_west_rosters.csv
│       ├── free_agent_pool.csv
│       └── sb_winners_combined.csv
│
├── src/
│   ├── __init__.py
│   ├── player_valuation.py          # ✅ COMPLETE - Bond pricing model
│   ├── evolution_engine.py          # ✅ COMPLETE - Genetic algorithm
│   ├── portfolio_optimizer.py       # 🔧 TODO - Efficient frontier
│   ├── sb_template.py               # ✅ COMPLETE - SB winner matching
│   ├── nfc_west_comparison.py       # 🔧 TODO - Division comparison framework
│   ├── visualizations.py            # 🔧 TODO - Plotly charts
│   │
│   ├── data_collection/
│   │   ├── __init__.py              # 🔧 MISSING - needs to be created
│   │   ├── nflfastr_collector.py    # ✅ COMPLETE - Performance data
│   │   ├── overthecap_scraper.py    # 🔧 INCOMPLETE - needs methods
│   │   ├── roster_builder.py        # 🔧 TODO - Merges data sources
│   │   └── data_processor.py        # 🔧 TODO - Feature engineering
│   │
│   └── agents/                      # 🔧 TODO - Multi-agent AI layer
│       ├── __init__.py
│       ├── coordinator_agent.py     # Orchestrates other agents
│       ├── contract_agent.py        # Cap/contract analysis
│       ├── scouting_agent.py        # Player scouting reports
│       ├── strategy_agent.py        # Game strategy insights
│       └── agent_system.py          # Entry point for agent system
│
├── streamlit_app/
│   ├── app.py                       # 🔧 TODO - Main dashboard
│   └── pages/
│       ├── 01_roster_analysis.py
│       ├── 02_nfc_west_comparison.py
│       ├── 03_evolution_results.py
│       ├── 04_sb_template.py
│       └── 05_ai_assistant.py
│
├── notebooks/
│   └── exploratory_analysis.ipynb
│
└── tests/
    ├── test_evaluation.py           # ✅ EXISTS (in src/, needs moving)
    └── test_evolution.py            # ✅ EXISTS (in src/, needs moving)
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

### `src/data_collection/nflfastr_collector.py`
Collects performance data via `nfl_data_py`:
```python
collector = NFLDataCollector()
data = collector.collect_all([2023, 2024, 2025])
# Returns dict: {pbp, stats, rosters, injuries}
```

---

## 🔧 Modules To Build

### Priority 1: Fix Broken Things
- [ ] Fix imports in `evolution_engine.py` (bare → relative)
- [ ] Fix imports in `test_evolution.py` and `test_evaluation.py`
- [ ] Remove undefined `main()` call in `player_valuation.py`
- [ ] Create `src/data_collection/__init__.py`
- [ ] Fix f-string formatting bug in `nflfastr_collector.py`

### Priority 2: Complete Data Collection
- [ ] Finish `overthecap_scraper.py` with 49ers/NFC West teams
- [ ] Build `roster_builder.py` to merge performance + contract data
- [ ] Build `data_processor.py` for feature engineering
- [ ] Create `collect_all_data.py` master script

### Priority 3: Analysis Modules
- [ ] `sb_template.py` - Super Bowl winner template matching
- [ ] `nfc_west_comparison.py` - Division comparison framework
- [ ] `portfolio_optimizer.py` - Efficient frontier analysis
- [ ] `visualizations.py` - Plotly charts

### Priority 4: AI Agent Layer (Critical for 49ers Role)
- [ ] `agents/coordinator_agent.py` - Orchestrates specialist agents
- [ ] `agents/contract_agent.py` - Natural language cap analysis
- [ ] `agents/scouting_agent.py` - Generates scouting reports
- [ ] `agents/strategy_agent.py` - Game strategy insights

### Priority 5: Dashboard
- [ ] `streamlit_app/app.py` - Main Streamlit dashboard
- [ ] Individual page modules

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
    # NFC West (Primary)
    "SF":  "san-francisco-49ers",
    "SEA": "seattle-seahawks",
    "LAR": "los-angeles-rams",
    "ARI": "arizona-cardinals",
    # Super Bowl Winners (Template Matching)
    "KC":  "kansas-city-chiefs",
    "TB":  "tampa-bay-buccaneers",
    "PHI": "philadelphia-eagles",
}
```

### 49ers 2026 Cap Context
- ~$71.7M in cap space
- ~$36M+ in dead money
- Key contracts: Purdy ($37.75M), Warner ($21M), Aiyuk ($24.9M),
  Kittle ($10.9M), McCaffrey ($10.5M)
- Needs: WR depth, pass rush, secondary
- Recently signed: Mike Evans ($14.5M/yr), Christian Kirk (1yr/$6M)

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
- "Generate a scouting report on George Kittle vs Rams"
- "How does our cap situation compare to the Seahawks?"
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
python src/test_evaluation.py        # Test valuation model
python src/test_evolution.py         # Test evolution engine
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
4. **Data files go in `data/`** - never commit raw data to git
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

This project is a portfolio piece for the **San Francisco 49ers Football
AI Fellow** position. The role emphasizes:

1. **AI tooling over pure analytics** - The multi-agent system is the
   headline feature, not just the valuation model
2. **Generative AI workflows** - Claude API agents that automate
   scouting and roster analysis
3. **Deployed applications** - Streamlit dashboard proves ability to
   ship working tools
4. **Communication** - Every output should be explainable to non-technical
   coaches and scouts
5. **Scouting integration** - Scouting report generator is a key feature

### Positioning Statement
> "An AI-powered football intelligence system that uses generative AI and
> multi-agent workflows to automate scouting reports, answer natural language
> roster questions, and evolve optimal roster configurations within hard
> cap constraints."

---

## 📝 TODO Checklist

### Immediate Fixes
- [ ] Fix bare imports → absolute imports everywhere
- [ ] Remove undefined `main()` in `player_valuation.py`
- [ ] Create `src/data_collection/__init__.py`
- [ ] Fix f-string bug in `nflfastr_collector.py`
- [ ] Move test files from `src/` to `tests/`

### Data Collection
- [ ] Complete `overthecap_scraper.py` for 49ers/NFC West
- [ ] Build `roster_builder.py`
- [ ] Create `collect_all_data.py`
- [ ] Run full data collection pipeline
- [ ] Validate merged data quality

### Core Models
- [ ] `sb_template.py` - SB winner similarity scoring
- [ ] `nfc_west_comparison.py` - Division comparison
- [ ] `visualizations.py` - Plotly charts

### AI Layer
- [ ] Claude API integration setup
- [ ] Coordinator agent
- [ ] Contract agent
- [ ] Scouting report generator
- [ ] Strategy agent

### Dashboard
- [ ] Streamlit app structure
- [ ] Roster analysis page
- [ ] NFC West comparison page
- [ ] Evolution results page
- [ ] SB template page
- [ ] AI assistant page

### Polish
- [ ] README.md
- [ ] Docstrings on all public methods
- [ ] Unit tests for core modules
- [ ] Demo video recording