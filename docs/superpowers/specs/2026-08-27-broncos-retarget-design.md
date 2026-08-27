# Broncos Retarget + Posting-Mapped Positioning — Design

**Date:** 2026-08-27
**Status:** Approved
**Context:** Retarget the roster-analysis portfolio project from the San
Francisco 49ers (Football AI Fellow) to the Denver Broncos, whose Analytics
Engineer posting closes September 6 (applying today). The posting is a
business-side role (ticketing, marketing, sponsorship, fan engagement), so
the project keeps its football domain but is repositioned to explicitly
demonstrate the posting's technical competencies.

## Decisions Made

1. **Full retarget** — new Broncos/AFC West data, re-run pipeline and
   evolution, update code, dashboard, and docs. (Rejected: docs-only
   reframe; team parameterization refactor.)
2. **Positioning** — the Claude multi-agent layer is a co-headline with the
   data pipeline and predictive modeling, because the posting explicitly
   names "agentic workflows, MCP, RAG, or LLM-powered applications" and
   "Claude" (preferred qualifications). (Revised from an earlier decision to
   demote the AI layer.)
3. **Honest framing** — README states plainly that roster construction is
   the demo domain and maps the machinery (scoring, segmentation,
   optimization) to the posting's business use cases (lead scoring, fan
   propensity). No pretense that this is a business-analytics project.

## 1. Data Layer

- Add OverTheCap `TEAM_SLUGS` entries: `DEN: denver-broncos`,
  `LAC: los-angeles-chargers`, `LV: las-vegas-raiders`. `KC` already exists
  (SB template team) and double-counts as a division rival.
- Scrape 2026 contracts for DEN, KC, LAC, LV into `data/raw/contracts/`
  (`den_2026.csv`, `kc_2026.csv`, `lac_2026.csv`, `lv_2026.csv`),
  respecting the existing 2-second rate limit.
- nflfastR performance data (2023–2025) is league-wide — no re-collection.
- Re-run `roster_builder` to produce `den_full_roster` /
  `afc_west_rosters.csv` and a Denver `player_assets_ready.csv`.
- Re-run the evolution engine on a **Denver-only pool** (mirroring commit
  `1dbcd27`, the SF-only-pool fix) to regenerate `evolution_results.json`.
- Replace old NFC West processed files; leave raw SF/SEA/LAR/ARI CSVs on
  disk (gitignored).

**Fallback:** if OverTheCap scraping breaks, hand-build the four contract
CSVs from OTC's pages so the pipeline still runs today.

## 2. Code Retarget

- Rename `src/nfc_west_comparison.py` → `src/afc_west_comparison.py` and
  `streamlit_app/pages/02_nfc_west_comparison.py` →
  `02_afc_west_comparison.py`; rename `tests/test_nfc_west_comparison.py`
  accordingly.
- Division list becomes `["DEN", "KC", "LAC", "LV"]`; scraper's `NFC_WEST`
  constant becomes `AFC_WEST`.
- All `primary_team="SF"` / `"SF"` defaults become `"DEN"`. Sweep the ~113
  hardcoded SF/NFC West references across the 18 affected files (agents,
  scripts, dashboard pages, tests).
- Team-agnostic modules (`player_valuation`, `evolution_engine`,
  `portfolio_optimizer`, `sb_template`) untouched except demo defaults.

## 3. Broncos Context Research

- Web-research Denver's actual 2026 cap situation: cap space, key contracts
  (Nix, Surtain, etc.), dead money, roster needs.
- Ground CLAUDE.md's cap-context section and the agents' injected context in
  verified numbers. Anything unverifiable is flagged, not invented.

## 4. Positioning Rewrite

README and CLAUDE.md rewritten for the Broncos, including a "How this maps
to the Analytics Engineer role" section keyed to the posting's language:

| Posting requirement | Project evidence |
|---|---|
| ETL pipelines, data integration | Multi-source pipeline (nflfastR + OverTheCap → model-ready datasets) |
| Predictive / propensity / scoring models | Player valuation, risk scoring, efficiency ratios |
| Agentic workflows, LLM apps, Claude | Claude multi-agent layer (coordinator + specialists) |
| Dashboards & storytelling | Streamlit dashboard, explainable to non-technical stakeholders |
| Model monitoring / refinement | Evolution engine + portfolio metrics |

Plus an explicit line that the same scoring/segmentation machinery applies
to lead scoring and fan-propensity modeling.

## 5. Verification

- Full test suite passes.
- Streamlit app launches; every page renders with Denver data.
- No stray "49ers"/"SF"/"NFC West" references in user-facing docs or
  dashboard (grep sweep).

## Sequencing

1. Scrape + Broncos research (highest external risk, do first)
2. Code sweep + renames
3. Pipeline re-run (roster build → valuation → evolution)
4. Docs/positioning rewrite
5. Verify (tests + app)
