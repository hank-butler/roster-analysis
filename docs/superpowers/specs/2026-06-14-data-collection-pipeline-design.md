# Data Collection Pipeline Design
**Date:** 2026-06-14  
**Priority:** 2 — Complete Data Collection  
**Goal:** Build and run a resumable 5-stage pipeline that collects NFL performance data and OTC contract data, merges them via fuzzy matching, engineers features, and outputs `PlayerAsset`-ready data.

---

## Overview

The pipeline ingests two independent data sources (nfl_data_py performance stats and OverTheCap contract data) that share no common player identifier. Stages save intermediate outputs to disk so any stage can be skipped or re-run independently — critical given slow external I/O (parquet downloads + rate-limited scraping).

---

## Stage 1 — Performance Collection
**Module:** `src/data_collection/nflfastr_collection.py` (already built)  
**Skip condition:** all 4 output files exist

**Outputs:**
- `data/raw/performance/pbp_2023_2025.parquet`
- `data/raw/performance/player_stats_2023_2025.csv`
- `data/raw/performance/rosters_2023_2025.csv`
- `data/raw/performance/injuries_2023_2025.csv`

---

## Stage 2 — Contract Scraping
**Module:** `src/data_collection/overthecap_scraper.py` (needs completing)  
**Skip condition:** all 7 team CSV files exist  
**Rate limit:** 2s minimum between requests

**Teams:**
- NFC West: SF, SEA, LAR, ARI (SF and ARI must be added to `TEAM_SLUGS`)
- SB Winners: KC, TB, PHI

**Methods to add:**
- `scrape_team(team: str) → pd.DataFrame` — fetches `overthecap.com/roster/{slug}`, parses contract table, saves CSV. Logs clear error with raw HTML snippet if table not found.
- `scrape_nfc_west() → Dict[str, pd.DataFrame]`
- `scrape_sb_winners() → Dict[str, pd.DataFrame]`
- `scrape_all() → Dict[str, pd.DataFrame]` — calls both above, skips teams with existing CSVs

**Columns extracted:** `player_name`, `position`, `age`, `cap_hit`, `base_salary`, `guaranteed_money`, `total_value`, `years_remaining`, `dead_cap`

**Outputs:**
- `data/raw/contracts/sf_2026.csv`
- `data/raw/contracts/sea_2026.csv`
- `data/raw/contracts/lar_2026.csv`
- `data/raw/contracts/ari_2026.csv`
- `data/raw/contracts/sb_winners/kc_2026.csv`
- `data/raw/contracts/sb_winners/tb_2026.csv`
- `data/raw/contracts/sb_winners/phi_2026.csv`

---

## Stage 3 — Roster Building + Merge
**Module:** `src/data_collection/roster_builder.py` (new)  
**Skip condition:** `nfc_west_rosters.csv` and `sb_winners_combined.csv` exist

**Why no shared ID:** `nfl_data_py` uses GSIS IDs (NFL's internal system); OTC uses its own independent player slugs. No official crosswalk exists between the two. Join key is `normalized_name + position + team`.

**Performance aggregation (3 seasons: 2023–2025):**
- `epa_total`: weighted decay — 2025: 50%, 2024: 30%, 2023: 20%
- `snaps_played`: raw 3-season sum (keeps `snap_factor` formula intact)
- `games_missed`: raw 3-season sum (keeps `injury_risk = games_missed / 51` formula intact)

**Fuzzy merge:**
- Tool: `rapidfuzz.fuzz.token_sort_ratio`
- Threshold: ≥85 score → matched, performance columns populated
- Below threshold → OTC player still included in merged CSV with null performance columns, and also logged to `unmatched_players.csv` for hand-fixing

**`unmatched_players.csv` columns:** `otc_name`, `otc_team`, `otc_position`, `nfl_name`, `nfl_team`, `nfl_position`, `match_score`

**Methods:**
- `load_performance_data() → pd.DataFrame`
- `load_contract_data(teams: List[str]) → pd.DataFrame`
- `merge(perf_df, contract_df) → pd.DataFrame`
- `build_nfc_west() → pd.DataFrame`
- `build_sb_winners() → pd.DataFrame`

**Outputs:**
- `data/processed/nfc_west_rosters.csv`
- `data/processed/sb_winners_combined.csv`
- `data/processed/unmatched_players.csv`

---

## Stage 4 — Feature Engineering
**Module:** `src/data_collection/data_processor.py` (new)  
**Skip condition:** `player_assets_ready.csv` exists

**Methods:**
- `load_merged_data(path) → pd.DataFrame`
- `compute_features(df) → pd.DataFrame` — fills null performance fields (epa_total, snaps_played, games_missed) with per-position averages computed from matched players in the same dataset (e.g., unmatched SF players get SF/NFC West matched-player averages by position)
- `enforce_schema(df) → pd.DataFrame` — renames columns to exact `PlayerAsset` field names (`cap_hit → cap_hit_2026`, `total_value → total_contract_value`, etc.), coerces types
- `to_player_assets(df) → List[PlayerAsset]` — instantiates `PlayerAsset` objects ready for `PlayerValuationModel.value_roster()`

**Output:**
- `data/processed/player_assets_ready.csv`

---

## Stage 5 — Validation
**Location:** inline in `collect_all_data.py`  
**No file output — prints summary report**

**Checks:**
- All required `PlayerAsset` fields present
- No nulls in critical numeric fields (`cap_hit_2026`, `epa_total`, `snaps_played`, `games_missed`)
- All position values are valid (15 known positions)
- `cap_hit_2026 > 0` for all players
- `age` within bounds (18–45)

**Summary report prints:**
- Total players loaded
- Players per team
- Fuzzy match rate (% matched vs. defaulted)
- Count of players using position-average defaults

---

## Orchestrator — `collect_all_data.py`

Runs from project root. Each stage prints `[SKIP]` or `[RUN]` status.

```bash
python collect_all_data.py                          # full run, skips cached stages
python collect_all_data.py --force-stage contracts  # re-run scraping only
python collect_all_data.py --force-stage merge      # re-run merge only
python collect_all_data.py --force-stage features   # re-run feature engineering only
python collect_all_data.py --force-stage validate   # re-run validation only
python collect_all_data.py --force-all              # full re-run, ignore all cached
```

---

## Key Constraints

- Rate limit OTC scraper: 2s minimum between requests
- Never commit raw data to git (`data/` is gitignored)
- Absolute imports throughout (`from src.data_collection...`)
- Google-style docstrings, type hints, 88-char lines
