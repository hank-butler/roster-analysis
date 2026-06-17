# NFL Roster Optimizer

A football intelligence system that treats NFL roster construction as a constrained portfolio optimization problem. Each player is modeled as a financial asset with an expected return (performance), a risk profile (injury and age), and a cost (salary-cap hit). A genetic algorithm searches the roster space under a hard cap and positional constraints, and a multi-agent layer built on the Claude API answers natural-language roster questions grounded in the underlying data.

This project is in active development. The valuation model, analysis modules, data pipeline, AI agent layer, and dashboard are functional; the evolution engine and several refinements are still being tuned (see [Status](#status)).

> **Note on scope:** This is a portfolio project built on public data. Valuation outputs are directional analytical tools, not authoritative player rankings. See [Model Notes & Limitations](#model-notes--limitations) for an honest account of what the numbers do and don't capture.

---

## Core Idea

A salary cap forces the same tradeoff a portfolio manager faces: maximize return for a fixed budget while managing risk. Framing a roster this way makes several questions precise:

- Which contracts deliver the most performance per cap dollar?
- Where is cap concentrated, and is that concentration justified by return?
- How does the team's structure compare to recent Super Bowl winners?
- Given a budget and positional requirements, what roster maximizes risk-adjusted value?

The financial analogy borrows from portfolio theory and bond-style valuation: expected value discounted by a risk score, efficiency ratios analogous to yield, and a Sharpe-style risk-adjusted return.

---

## Architecture

```
Data Sources                Analysis Layer              Interface
------------                --------------              ---------
nfl_data_py  ─┐
              ├─► RosterBuilder ─► PlayerValuationModel ─┬─► Streamlit dashboard
OverTheCap   ─┘   (fuzzy merge)    (per-player metrics)  │
                                                         ├─► AI agent system
                  DataProcessor    PortfolioAnalyzer     │   (Claude API)
                  (features)       (roster metrics)      │
                                                         │
                                   EvolutionEngine ──────┘
                                   (genetic algorithm)

                                   SuperBowlTemplateAnalyzer
                                   DivisionAnalyzer (NFC West)
```

The pipeline ingests two independent public sources that share no common player ID, fuzzy-merges them, engineers features, and produces a model-ready dataset. The analysis modules consume that dataset; the dashboard and AI layer consume the analysis modules.

---

## Components

**Player valuation (`src/player_valuation.py`).** Assigns each player an expected value (position baseline plus EPA-derived performance, scaled by snap share), a risk score (injury history, age relative to positional peak, positional longevity), a fair value (expected value discounted by risk), an efficiency ratio (value per cap dollar), and a Sharpe-style risk-adjusted return. `PortfolioAnalyzer` aggregates these to the roster level and flags over- and under-valued contracts.

**Data pipeline (`collect_all_data.py`, `src/data_collection/`).** A resumable five-stage pipeline: collect performance data via `nfl_data_py`, scrape contract data from OverTheCap, fuzzy-merge the two on normalized name and team, engineer features and enforce the `PlayerAsset` schema, then validate. Each stage checkpoints to disk and skips if its outputs already exist; individual stages can be forced with `--force-stage`.

**Evolution engine (`src/evolution_engine.py`).** A genetic algorithm that searches for high-fitness 53-man rosters under cap and positional constraints. Fitness is a weighted combination of portfolio efficiency (40%), inverted risk (25%), positional balance (20%), and cap utilization (15%). *In active development.*

**How the genetic algorithm works.** Each chromosome represents one complete roster configuration; each gene is a player selection. The engine initialises a population of random valid rosters, then iterates: fitness is evaluated for every chromosome, the top individuals are carried forward unchanged (elitism), and the rest are produced by tournament selection, position-aware crossover (each position group is inherited wholesale from one parent or the other at random), and random mutation (swap, replace, or upgrade a single player). A repair step after crossover trims over-filled positions and fills under-filled ones to keep offspring valid. The fitness score is a real number between 0 and 1, where 1 is the theoretical maximum: a perfectly efficient, low-risk, positionally balanced roster at 90–95% cap utilisation. Invalid rosters — wrong size, missing positions, over cap — receive −1000, which eliminates them immediately from selection. For the demo the engine optimises within SF's current contracted player pool, which is an honest reflection of available data rather than a simulated free-agency market; cross-team acquisition modelling is planned future work.

**Super Bowl template matching (`src/sb_template.py`).** Scores a roster's structure — position-group cap allocation, age distribution, and star concentration — against averages from recent Super Bowl winners, and reports the largest structural gaps.

**Division comparison (`src/nfc_west_comparison.py`).** Coordinates the above across the NFC West, producing comparative metrics, rankings, and figures, plus a strengths / weaknesses / opportunities read for a primary team.

**AI agent layer (`src/agents/`).** A multi-agent system on the Claude API. A coordinator routes each natural-language query to one of three specialists — contract (cap and valuation analysis), scouting (player assessments), or strategy (team-level roster construction). Each specialist answers using only data injected from the pipeline, with instructions never to invent figures. Stateless, one routing call plus one response call per query.

**Dashboard (`streamlit_app/`).** A six-page Streamlit app demonstrating each system: roster valuation, division comparison, evolution results, Super Bowl template matching, and the AI assistant.

---

## Quickstart

Requires Python 3.11.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Build the dataset (downloads performance data + scrapes contracts; resumable)
python collect_all_data.py

# 3. Launch the dashboard
streamlit run streamlit_app/app.py
```

To use the AI assistant page, set an Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

The first pipeline run downloads several hundred MB of play-by-play data and is slow; subsequent runs use the cached files.

---

## Testing

```bash
pytest tests/ -v
```

The suite covers the valuation model, data pipeline (HTML parsing, fuzzy merge, feature engineering, schema enforcement), analysis modules, and the agent layer. Agent tests mock the Claude API — no network calls or API key required to run the tests.

---

## Model Notes & Limitations

This section is deliberately prominent: the model's value depends on knowing where it is and isn't reliable.

- **EPA is the only performance signal.** It works well for QBs and skill positions but is a weak proxy for offensive line, defensive line, and linebackers, whose contributions don't surface cleanly in scoring EPA. Valuations for those groups are directional — useful for relative cap-allocation analysis, not absolute player quality. (For example, elite pass rushers tend to look "overvalued" because pressure and disruption aren't fully captured; read that as a cap-concentration flag, not a verdict on the player.)
- **`total_contract_value` is not currently parsed** from the OverTheCap salary-cap page (it renders in a multi-scenario format that doesn't extract cleanly); `cap_hit` and `guaranteed_money` are reliable. The bond-style NPV calculation is implemented but not yet wired into the default valuation path for this reason.
- **Strongest signal:** QB and skill-position comparisons, cap-concentration analysis, and free-agency / draft target prioritization.
- **Weakest signal:** absolute cross-position player rankings and OL/DL/LB evaluation.

Full analytical notes are in [`docs/model_insights.md`](docs/model_insights.md).

---

## Tech Stack

Python 3.11 · pandas · numpy · nfl_data_py · BeautifulSoup / rapidfuzz (data) · Plotly (visualization) · Streamlit (dashboard) · Anthropic Claude API (agent layer) · pytest (testing).

---

## Status

| Component | Status |
|---|---|
| Player valuation model | Functional |
| Data collection pipeline | Functional |
| Super Bowl template matching | Functional |
| Division comparison | Functional |
| AI agent layer | Functional |
| Streamlit dashboard | Functional |
| Evolution engine | In development — tuning |
| `total_contract_value` parsing / NPV integration | Planned |

---

## License

MIT — see [LICENSE](LICENSE).
