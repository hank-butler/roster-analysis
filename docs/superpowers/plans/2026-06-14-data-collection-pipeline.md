# Data Collection Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a resumable 5-stage pipeline that collects NFL performance data and OTC contract data, merges them via fuzzy matching, and outputs `PlayerAsset`-ready CSVs for the 49ers, NFC West, and Super Bowl winner teams.

**Architecture:** Staged pipeline with disk-based checkpointing — each stage saves output CSVs and skips if outputs already exist. nfl_data_py provides performance stats (EPA, games, snap counts). OverTheCap is scraped via `pd.read_html()` for contract data. The two sources are fuzzy-joined on normalized player name + position + team since no shared player ID exists.

**Tech Stack:** Python 3.11, pandas, nfl_data_py, requests, beautifulsoup4, lxml, rapidfuzz, pytest

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `src/data_collection/nflfastr_collection.py` | Complete | Stage 1: download performance data |
| `src/data_collection/overthecap_scraper.py` | Extend | Stage 2: scrape OTC contract data |
| `src/data_collection/roster_builder.py` | Create | Stage 3: aggregate perf stats + fuzzy-merge with contracts |
| `src/data_collection/data_processor.py` | Create | Stage 4: feature engineering + PlayerAsset schema enforcement |
| `src/data_collection/__init__.py` | Update | export all collector classes |
| `collect_all_data.py` | Create | orchestrator with `--force-stage` flags |
| `tests/test_overthecap_scraper.py` | Create | unit tests for HTML parsing + currency cleaning |
| `tests/test_roster_builder.py` | Create | unit tests for EPA aggregation + fuzzy merge |
| `tests/test_data_processor.py` | Create | unit tests for schema enforcement + feature fill |
| `tests/fixtures/sample_otc.html` | Create | fixture HTML for scraper tests |

---

### Task 1: Install missing dependencies and run Stage 1 (performance data)

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Install `rapidfuzz` and `lxml`, update requirements.txt**

```bash
conda run -n nfl_analytics pip install rapidfuzz lxml
```

Add to `requirements.txt` under `# Utilities`:
```
rapidfuzz==3.9.0
lxml==5.2.2
```

- [ ] **Step 2: Run Stage 1 — collect performance data**

This downloads ~500MB of parquet data on first run. Start it early; it caches after the first run.

```bash
conda activate nfl_analytics
cd /home/hankbutler/Desktop/Projects/roster-analysis
python -c "
from src.data_collection.nflfastr_collection import NFLDataCollector
collector = NFLDataCollector()
data = collector.collect_all([2023, 2024, 2025])
print('Columns in stats:', list(data['stats'].columns[:30]))
print('Columns in rosters:', list(data['rosters'].columns[:20]))
print('Stats shape:', data['stats'].shape)
"
```

Expected output (inspect and note actual column names — they inform Task 3):
```
Columns in stats: ['player_id', 'player_name', 'player_display_name', 'position',
  'recent_team', 'season', 'games', 'passing_epa', 'rushing_epa', 'receiving_epa', ...]
Stats shape: (roughly 2000-3000, 50+)
```

- [ ] **Step 3: Check for snap count data**

```bash
conda run -n nfl_analytics python -c "
import nfl_data_py as nfl
snaps = nfl.import_snap_counts([2024])
print('Snap columns:', list(snaps.columns))
print('Sample:', snaps.head(2))
"
```

Note the exact column names for offense/defense snaps — needed in Task 3.

- [ ] **Step 4: Verify files were saved**

```bash
ls data/raw/performance/
```

Expected:
```
injuries_2023_2025.csv  pbp_2023_2025.parquet  player_stats_2023_2025.csv  rosters_2023_2025.csv
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "feat: add rapidfuzz and lxml dependencies"
```

---

### Task 2: Complete the OTC Scraper (Stage 2)

**Files:**
- Create: `tests/fixtures/sample_otc.html`
- Create: `tests/test_overthecap_scraper.py`
- Modify: `src/data_collection/overthecap_scraper.py`

- [ ] **Step 1: Create HTML fixture**

Create `tests/fixtures/sample_otc.html`:

```html
<!DOCTYPE html>
<html>
<body>
<table>
  <thead>
    <tr>
      <th>Player</th>
      <th>Pos</th>
      <th>Age</th>
      <th>Base Salary</th>
      <th>Signing Bonus</th>
      <th>Cap Hit</th>
      <th>Dead Cap</th>
      <th>Total Value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Brock Purdy</td>
      <td>QB</td>
      <td>26</td>
      <td>$1,080,000</td>
      <td>$36,670,000</td>
      <td>$37,750,000</td>
      <td>$11,130,000</td>
      <td>$244,200,000</td>
    </tr>
    <tr>
      <td>George Kittle</td>
      <td>TE</td>
      <td>31</td>
      <td>$10,900,000</td>
      <td>$0</td>
      <td>$10,900,000</td>
      <td>$5,450,000</td>
      <td>$75,000,000</td>
    </tr>
    <tr>
      <td>Brandon Aiyuk</td>
      <td>WR</td>
      <td>27</td>
      <td>$4,900,000</td>
      <td>$20,000,000</td>
      <td>$24,900,000</td>
      <td>$35,000,000</td>
      <td>$120,000,000</td>
    </tr>
  </tbody>
</table>
</body>
</html>
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_overthecap_scraper.py`:

```python
import pytest
import pandas as pd
from pathlib import Path
from src.data_collection.overthecap_scraper import OverTheCapScraper

FIXTURE_HTML = Path(__file__).parent / "fixtures" / "sample_otc.html"


def test_parse_html_table_returns_dataframe():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_parse_html_extracts_required_columns():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    required = {"player_name", "position", "age", "cap_hit", "total_value", "team"}
    assert required.issubset(set(df.columns))


def test_parse_html_converts_currency_to_float():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert df["cap_hit"].dtype == float
    assert df.loc[df["player_name"] == "Brock Purdy", "cap_hit"].iloc[0] == 37_750_000.0


def test_parse_html_adds_team_column():
    scraper = OverTheCapScraper()
    html = FIXTURE_HTML.read_text()
    df = scraper._parse_roster_html(html, team="SF")
    assert (df["team"] == "SF").all()


def test_team_slugs_contains_all_required_teams():
    scraper = OverTheCapScraper()
    required_teams = {"SF", "SEA", "LAR", "ARI", "KC", "TB", "PHI"}
    assert required_teams.issubset(set(scraper.TEAM_SLUGS.keys()))
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_overthecap_scraper.py -v
```

Expected: 5 failures (methods not yet implemented).

- [ ] **Step 4: Implement the OTC Scraper methods**

Replace `src/data_collection/overthecap_scraper.py` with:

```python
import re
import time
import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OverTheCapScraper:
    """Scrapes overthecap.com for team contract data."""

    BASE_URL = "https://overthecap.com/roster/"

    TEAM_SLUGS = {
        "SF":  "san-francisco-49ers",
        "SEA": "seattle-seahawks",
        "LAR": "los-angeles-rams",
        "ARI": "arizona-cardinals",
        "KC":  "kansas-city-chiefs",
        "TB":  "tampa-bay-buccaneers",
        "PHI": "philadelphia-eagles",
        # Legacy teams kept for reference
        "IND": "indianapolis-colts",
        "HOU": "houston-texans",
    }

    NFC_WEST = ["SF", "SEA", "LAR", "ARI"]
    SB_WINNERS = ["KC", "TB", "PHI"]

    def __init__(self, output_dir: str = "data/raw/contracts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "sb_winners").mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })

    @staticmethod
    def _parse_currency(value: str) -> float:
        """Convert OTC currency string like '$37,750,000' to float."""
        if pd.isna(value):
            return 0.0
        cleaned = re.sub(r"[$,\s]", "", str(value))
        if not cleaned or cleaned in ("—", "-", ""):
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_roster_html(self, html: str, team: str) -> pd.DataFrame:
        """Parse OTC roster page HTML into a clean DataFrame.

        Args:
            html: Raw HTML string from the OTC roster page.
            team: Team abbreviation to tag rows with (e.g., 'SF').

        Returns:
            DataFrame with columns: player_name, position, age, cap_hit,
            base_salary, total_value, dead_cap, team.
        """
        try:
            tables = pd.read_html(html)
        except ValueError:
            logger.error(f"[{team}] No HTML tables found. First 500 chars: {html[:500]}")
            return pd.DataFrame()

        if not tables:
            logger.error(f"[{team}] pd.read_html returned empty list.")
            return pd.DataFrame()

        # Pick the largest table — it's the contracts table
        df = max(tables, key=len).copy()
        logger.info(f"[{team}] Found table with columns: {list(df.columns)}")

        # Normalize column names: lowercase, strip spaces
        df.columns = [str(c).lower().strip() for c in df.columns]

        # Map OTC column names to our standard names
        col_map = {
            "player": "player_name",
            "pos":    "position",
            "age":    "age",
            "base salary": "base_salary",
            "cap hit": "cap_hit",
            "dead cap": "dead_cap",
            "total value": "total_value",
            "total": "total_value",
            "guaranteed": "guaranteed_money",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Ensure required columns exist with defaults
        for col in ["player_name", "position", "age", "cap_hit", "total_value",
                    "base_salary", "dead_cap", "guaranteed_money"]:
            if col not in df.columns:
                df[col] = 0 if col != "player_name" else ""

        # Parse currency columns
        for col in ["cap_hit", "base_salary", "total_value", "dead_cap", "guaranteed_money"]:
            df[col] = df[col].apply(self._parse_currency)

        # Parse age to int
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(0).astype(int)

        # Drop rows with no player name or $0 cap hit (often header repeat rows)
        df = df[df["player_name"].astype(str).str.strip() != ""]
        df = df[df["player_name"].astype(str) != "nan"]

        df["team"] = team

        # years_remaining: OTC roster page doesn't expose this directly — default 1
        # Hand-populate from unmatched_players.csv review if precision is needed
        if "years_remaining" not in df.columns:
            df["years_remaining"] = 1

        return df.reset_index(drop=True)

    def _output_path(self, team: str) -> Path:
        """Return the output CSV path for a given team abbreviation."""
        if team in self.SB_WINNERS:
            return self.output_dir / "sb_winners" / f"{team.lower()}_2026.csv"
        return self.output_dir / f"{team.lower()}_2026.csv"

    def scrape_team(self, team: str) -> Optional[pd.DataFrame]:
        """Scrape one team's roster page from OTC.

        Args:
            team: Team abbreviation (e.g., 'SF').

        Returns:
            DataFrame of contract data, or None on failure.
        """
        output_path = self._output_path(team)
        if output_path.exists():
            logger.info(f"[SKIP] {team}: {output_path} already exists")
            return pd.read_csv(output_path)

        slug = self.TEAM_SLUGS.get(team)
        if not slug:
            logger.error(f"[{team}] No slug configured. Add to TEAM_SLUGS.")
            return None

        url = f"{self.BASE_URL}{slug}"
        logger.info(f"[RUN]  {team}: fetching {url}")

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"[{team}] HTTP error: {e}")
            return None

        df = self._parse_roster_html(response.text, team=team)
        if df.empty:
            logger.error(f"[{team}] Parsing returned empty DataFrame — check HTML structure.")
            return None

        df.to_csv(output_path, index=False)
        logger.info(f"[{team}] Saved {len(df)} players to {output_path}")

        time.sleep(2)  # rate limit: 2s between requests
        return df

    def scrape_nfc_west(self) -> Dict[str, pd.DataFrame]:
        """Scrape all 4 NFC West teams."""
        results = {}
        for team in self.NFC_WEST:
            df = self.scrape_team(team)
            if df is not None:
                results[team] = df
        return results

    def scrape_sb_winners(self) -> Dict[str, pd.DataFrame]:
        """Scrape KC, TB, PHI Super Bowl winner teams."""
        results = {}
        for team in self.SB_WINNERS:
            df = self.scrape_team(team)
            if df is not None:
                results[team] = df
        return results

    def scrape_all(self) -> Dict[str, pd.DataFrame]:
        """Scrape all configured teams. Skips teams with existing CSVs."""
        results = {}
        results.update(self.scrape_nfc_west())
        results.update(self.scrape_sb_winners())
        logger.info(f"Scraping complete. Teams collected: {list(results.keys())}")
        return results
```

- [ ] **Step 5: Run tests — expect them to pass**

```bash
conda run -n nfl_analytics pytest tests/test_overthecap_scraper.py -v
```

Expected:
```
PASSED tests/test_overthecap_scraper.py::test_parse_html_table_returns_dataframe
PASSED tests/test_overthecap_scraper.py::test_parse_html_extracts_required_columns
PASSED tests/test_overthecap_scraper.py::test_parse_html_converts_currency_to_float
PASSED tests/test_overthecap_scraper.py::test_parse_html_adds_team_column
PASSED tests/test_overthecap_scraper.py::test_team_slugs_contains_all_required_teams
5 passed
```

- [ ] **Step 6: Run Stage 2 — scrape OTC live**

```bash
conda run -n nfl_analytics python -c "
from src.data_collection.overthecap_scraper import OverTheCapScraper
scraper = OverTheCapScraper()
results = scraper.scrape_all()
for team, df in results.items():
    print(f'{team}: {len(df)} players, columns={list(df.columns)}')
"
```

If any team's DataFrame is empty, OTC's HTML structure changed. Run this to inspect:
```bash
conda run -n nfl_analytics python -c "
import requests
r = requests.get('https://overthecap.com/roster/san-francisco-49ers',
    headers={'User-Agent': 'Mozilla/5.0'})
print(r.text[:3000])
"
```
Find the table structure and update the `col_map` dict in `_parse_roster_html` accordingly.

- [ ] **Step 7: Verify output files**

```bash
ls data/raw/contracts/
ls data/raw/contracts/sb_winners/
head -3 data/raw/contracts/sf_2026.csv
```

- [ ] **Step 8: Commit**

```bash
git add src/data_collection/overthecap_scraper.py \
        tests/test_overthecap_scraper.py \
        tests/fixtures/sample_otc.html
git commit -m "feat: complete OTC scraper with fuzzy-merge-ready output"
```

---

### Task 3: Build RosterBuilder (Stage 3)

**Files:**
- Create: `tests/test_roster_builder.py`
- Create: `src/data_collection/roster_builder.py`

**Context:** nfl_data_py's `import_seasonal_data` returns one row per player per season. Relevant columns (verify against Task 1 Step 2 output):
- `player_id`, `player_name`, `recent_team`, `position`, `season`, `games`
- `passing_epa`, `rushing_epa`, `receiving_epa` (NaN for non-skill positions)
- Snap counts may be in `offense_snaps` / `defense_snaps` or require `import_snap_counts`

- [ ] **Step 1: Write failing tests**

Create `tests/test_roster_builder.py`:

```python
import pytest
import pandas as pd
import numpy as np
from src.data_collection.roster_builder import RosterBuilder


# ---------- Fixtures ----------

@pytest.fixture
def sample_stats() -> pd.DataFrame:
    """Three-season stats for two players."""
    return pd.DataFrame([
        # Kittle: TE, SF — all 3 seasons
        {"player_id": "k001", "player_name": "George Kittle", "recent_team": "SF",
         "position": "TE", "season": 2023, "games": 16, "passing_epa": 0.0,
         "rushing_epa": 0.0, "receiving_epa": 12.0, "offense_snaps": 800},
        {"player_id": "k001", "player_name": "George Kittle", "recent_team": "SF",
         "position": "TE", "season": 2024, "games": 14, "passing_epa": 0.0,
         "rushing_epa": 0.0, "receiving_epa": 10.0, "offense_snaps": 700},
        {"player_id": "k001", "player_name": "George Kittle", "recent_team": "SF",
         "position": "TE", "season": 2025, "games": 17, "passing_epa": 0.0,
         "rushing_epa": 0.0, "receiving_epa": 15.0, "offense_snaps": 900},
        # Purdy: QB, SF — only 2 seasons (tests proration)
        {"player_id": "p001", "player_name": "Brock Purdy", "recent_team": "SF",
         "position": "QB", "season": 2024, "games": 16, "passing_epa": 30.0,
         "rushing_epa": 2.0, "receiving_epa": 0.0, "offense_snaps": 1000},
        {"player_id": "p001", "player_name": "Brock Purdy", "recent_team": "SF",
         "position": "QB", "season": 2025, "games": 17, "passing_epa": 35.0,
         "rushing_epa": 3.0, "receiving_epa": 0.0, "offense_snaps": 1050},
    ])


@pytest.fixture
def sample_contracts() -> pd.DataFrame:
    return pd.DataFrame([
        {"player_name": "George Kittle", "position": "TE", "team": "SF",
         "cap_hit": 10_900_000.0, "total_value": 75_000_000.0,
         "guaranteed_money": 0.0, "years_remaining": 1, "age": 31},
        {"player_name": "Brock Purdy", "position": "QB", "team": "SF",
         "cap_hit": 37_750_000.0, "total_value": 244_200_000.0,
         "guaranteed_money": 0.0, "years_remaining": 1, "age": 26},
        {"player_name": "Brandon Aiyuk", "position": "WR", "team": "SF",
         "cap_hit": 24_900_000.0, "total_value": 120_000_000.0,
         "guaranteed_money": 0.0, "years_remaining": 1, "age": 27},
    ])


# ---------- EPA Aggregation ----------

def test_epa_weighted_decay_three_seasons(sample_stats):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 2023: 12 * 0.2 = 2.4, 2024: 10 * 0.3 = 3.0, 2025: 15 * 0.5 = 7.5 → total = 12.9
    assert abs(kittle["epa_total"] - 12.9) < 0.01


def test_epa_prorated_when_seasons_missing(sample_stats):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats)
    purdy = agg[agg["player_name"] == "Brock Purdy"].iloc[0]
    # Only 2024 and 2025. Weights: 2024=0.3, 2025=0.5. Prorated to sum=1.0:
    # 2024 weight = 0.3/0.8 = 0.375, 2025 weight = 0.5/0.8 = 0.625
    # 2024 EPA = 32.0, 2025 EPA = 38.0
    # expected = 32.0 * 0.375 + 38.0 * 0.625 = 12.0 + 23.75 = 35.75
    expected = 32.0 * (0.3 / 0.8) + 38.0 * (0.5 / 0.8)
    assert abs(purdy["epa_total"] - expected) < 0.01


def test_games_missed_raw_sum(sample_stats):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 2023: 17-16=1, 2024: 17-14=3, 2025: 17-17=0 → total = 4
    assert kittle["games_missed"] == 4


def test_snaps_raw_sum(sample_stats):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 800 + 700 + 900 = 2400
    assert kittle["snaps_played"] == 2400


# ---------- Fuzzy Merge ----------

def test_merge_exact_match(sample_stats, sample_contracts):
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats)
    merged = builder.merge(perf, sample_contracts)
    kittle = merged[merged["player_name"] == "George Kittle"]
    assert len(kittle) == 1
    assert kittle.iloc[0]["cap_hit"] == 10_900_000.0


def test_unmatched_player_included_with_nulls(sample_stats, sample_contracts):
    """Aiyuk is in contracts but has no performance data — must still appear."""
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats)
    merged = builder.merge(perf, sample_contracts)
    aiyuk = merged[merged["player_name"] == "Brandon Aiyuk"]
    assert len(aiyuk) == 1
    assert pd.isna(aiyuk.iloc[0]["epa_total"])


def test_unmatched_log_written(sample_stats, sample_contracts, tmp_path):
    builder = RosterBuilder(output_dir=str(tmp_path))
    perf = builder._aggregate_performance(sample_stats)
    builder.merge(perf, sample_contracts)
    unmatched_path = tmp_path / "unmatched_players.csv"
    assert unmatched_path.exists()
    unmatched = pd.read_csv(unmatched_path)
    # Aiyuk has no perf match
    assert "Brandon Aiyuk" in unmatched["otc_name"].values
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_roster_builder.py -v
```

Expected: all fail with `ModuleNotFoundError` or `AttributeError`.

- [ ] **Step 3: Implement RosterBuilder**

Create `src/data_collection/roster_builder.py`:

```python
import re
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# EPA weighting: most recent season matters most
EPA_WEIGHTS = {2025: 0.5, 2024: 0.3, 2023: 0.2}
FUZZY_THRESHOLD = 85
GAMES_PER_SEASON = 17

# nfl_data_py team code normalizer (some datasets use 'LA' for Rams)
TEAM_NORMALIZER = {
    "LA": "LAR",
    "LV": "LV",
    "OAK": "LV",
}


def _normalize_team(team: str) -> str:
    return TEAM_NORMALIZER.get(str(team).upper(), str(team).upper())


def _normalize_name(name: str) -> str:
    """Lowercase, remove suffixes and punctuation for fuzzy matching."""
    name = str(name).lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    return " ".join(name.split())


class RosterBuilder:
    """Aggregates nfl_data_py performance stats and fuzzy-merges with OTC contract data."""

    def __init__(self, perf_dir: str = "data/raw/performance",
                 contract_dir: str = "data/raw/contracts",
                 output_dir: str = "data/processed"):
        self.perf_dir = Path(perf_dir)
        self.contract_dir = Path(contract_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Performance aggregation
    # ------------------------------------------------------------------

    def _aggregate_performance(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate multi-season stats into single per-player rows.

        EPA uses weighted decay (2025: 50%, 2024: 30%, 2023: 20%), prorated
        if a player doesn't appear in all three seasons.
        Snaps and games_missed are raw sums across all seasons.

        Args:
            stats_df: DataFrame from nfl_data_py.import_seasonal_data, one row
                      per player per season. Must have columns: player_name,
                      recent_team, position, season, games. EPA columns
                      (passing_epa, rushing_epa, receiving_epa) and snap
                      columns (offense_snaps, defense_snaps) are optional.

        Returns:
            DataFrame with one row per player: player_name, team, position,
            epa_total, snaps_played, games_missed.
        """
        df = stats_df.copy()
        df["team"] = df["recent_team"].apply(_normalize_team)

        # Compute total EPA per player-season
        epa_cols = [c for c in ["passing_epa", "rushing_epa", "receiving_epa"]
                    if c in df.columns]
        if epa_cols:
            df["season_epa"] = df[epa_cols].fillna(0).sum(axis=1)
        else:
            logger.warning("No EPA columns found — epa_total will be 0")
            df["season_epa"] = 0.0

        # Compute snaps per player-season
        snap_cols = [c for c in ["offense_snaps", "defense_snaps"]
                     if c in df.columns]
        if snap_cols:
            df["season_snaps"] = df[snap_cols].fillna(0).sum(axis=1)
            logger.info(f"Using snap columns: {snap_cols}")
        else:
            df["season_snaps"] = df.get("games", 0).fillna(0) * 65
            logger.warning("No snap columns found — using games * 65 as proxy")

        # Compute games missed per player-season
        df["season_games_missed"] = GAMES_PER_SEASON - df.get("games", 0).fillna(0)

        # Group by player, aggregating across seasons
        records = []
        grouped = df.groupby(["player_name", "team", "position"])

        for (player_name, team, position), group in grouped:
            # Weighted EPA (prorated for missing seasons)
            available_weights = {
                yr: w for yr, w in EPA_WEIGHTS.items()
                if yr in group["season"].values
            }
            total_weight = sum(available_weights.values())
            if total_weight == 0:
                epa_total = 0.0
            else:
                epa_total = sum(
                    group.loc[group["season"] == yr, "season_epa"].sum()
                    * (w / total_weight)
                    for yr, w in available_weights.items()
                )

            snaps_played = int(group["season_snaps"].sum())
            games_missed = int(group["season_games_missed"].sum())

            records.append({
                "player_name": player_name,
                "team": team,
                "position": position,
                "epa_total": round(epa_total, 4),
                "snaps_played": snaps_played,
                "games_missed": games_missed,
            })

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Contract loading
    # ------------------------------------------------------------------

    def load_performance_data(self) -> pd.DataFrame:
        """Load and aggregate performance data from Stage 1 CSVs."""
        stats_path = self.perf_dir / "player_stats_2023_2025.csv"
        if not stats_path.exists():
            raise FileNotFoundError(
                f"{stats_path} not found. Run Stage 1 first: "
                "python collect_all_data.py --force-stage performance"
            )
        stats_df = pd.read_csv(stats_path)
        logger.info(f"Loaded {len(stats_df)} player-season rows from {stats_path}")
        return self._aggregate_performance(stats_df)

    def load_contract_data(self, teams: List[str]) -> pd.DataFrame:
        """Load OTC contract CSVs for the given team abbreviations."""
        frames = []
        for team in teams:
            if team in ["KC", "TB", "PHI"]:
                path = self.contract_dir / "sb_winners" / f"{team.lower()}_2026.csv"
            else:
                path = self.contract_dir / f"{team.lower()}_2026.csv"

            if not path.exists():
                logger.warning(f"[{team}] Contract file not found: {path}. Skipping.")
                continue
            df = pd.read_csv(path)
            frames.append(df)

        if not frames:
            raise FileNotFoundError(
                "No contract CSVs found. Run Stage 2 first: "
                "python collect_all_data.py --force-stage contracts"
            )
        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Fuzzy merge
    # ------------------------------------------------------------------

    def merge(self, perf_df: pd.DataFrame,
              contract_df: pd.DataFrame) -> pd.DataFrame:
        """Fuzzy-merge performance stats onto contract rows.

        For each OTC player, find the best-matching performance row using
        normalized name + position + team. Matched rows get performance columns
        populated; unmatched rows stay in the output with NaN performance fields
        and are also logged to unmatched_players.csv.

        Args:
            perf_df: Output of _aggregate_performance().
            contract_df: Loaded OTC contract DataFrame.

        Returns:
            Merged DataFrame (one row per OTC player).
        """
        perf_df = perf_df.copy()
        contract_df = contract_df.copy()

        perf_df["_norm_name"] = perf_df["player_name"].apply(_normalize_name)
        perf_df["_norm_team"] = perf_df["team"].apply(_normalize_team)
        contract_df["_norm_name"] = contract_df["player_name"].apply(_normalize_name)
        contract_df["_norm_team"] = contract_df.get("team", pd.Series(dtype=str)).apply(
            _normalize_team
        )

        matched_rows = []
        unmatched_rows = []

        perf_cols = ["epa_total", "snaps_played", "games_missed"]

        for _, otc_row in contract_df.iterrows():
            otc_name = otc_row["_norm_name"]
            otc_team = otc_row["_norm_team"]
            otc_pos = str(otc_row.get("position", "")).upper()

            # Filter performance candidates: same team + position
            candidates = perf_df[
                (perf_df["_norm_team"] == otc_team) &
                (perf_df["position"].str.upper() == otc_pos)
            ]

            best_score = 0
            best_match = None

            for _, perf_row in candidates.iterrows():
                score = fuzz.token_sort_ratio(otc_name, perf_row["_norm_name"])
                if score > best_score:
                    best_score = score
                    best_match = perf_row

            merged_row = otc_row.drop(labels=["_norm_name", "_norm_team"]).to_dict()

            if best_match is not None and best_score >= FUZZY_THRESHOLD:
                for col in perf_cols:
                    merged_row[col] = best_match[col]
            else:
                for col in perf_cols:
                    merged_row[col] = np.nan
                unmatched_rows.append({
                    "otc_name": otc_row["player_name"],
                    "otc_team": otc_row.get("team", ""),
                    "otc_position": otc_pos,
                    "nfl_name": best_match["player_name"] if best_match is not None else "",
                    "nfl_team": best_match["team"] if best_match is not None else "",
                    "nfl_position": best_match["position"] if best_match is not None else "",
                    "match_score": best_score,
                })

            matched_rows.append(merged_row)

        merged_df = pd.DataFrame(matched_rows)

        unmatched_path = self.output_dir / "unmatched_players.csv"
        if unmatched_rows:
            pd.DataFrame(unmatched_rows).to_csv(unmatched_path, index=False)
            logger.info(
                f"{len(unmatched_rows)} unmatched players written to {unmatched_path}"
            )
        else:
            pd.DataFrame(columns=[
                "otc_name", "otc_team", "otc_position",
                "nfl_name", "nfl_team", "nfl_position", "match_score"
            ]).to_csv(unmatched_path, index=False)

        return merged_df.drop(columns=["_norm_name", "_norm_team"], errors="ignore")

    # ------------------------------------------------------------------
    # Build outputs
    # ------------------------------------------------------------------

    def build_nfc_west(self) -> pd.DataFrame:
        """Build and save nfc_west_rosters.csv."""
        output_path = self.output_dir / "nfc_west_rosters.csv"
        if output_path.exists():
            logger.info(f"[SKIP] {output_path} already exists")
            return pd.read_csv(output_path)

        perf = self.load_performance_data()
        contracts = self.load_contract_data(["SF", "SEA", "LAR", "ARI"])
        merged = self.merge(perf, contracts)
        merged.to_csv(output_path, index=False)
        logger.info(f"Saved NFC West roster ({len(merged)} players) to {output_path}")
        return merged

    def build_sb_winners(self) -> pd.DataFrame:
        """Build and save sb_winners_combined.csv."""
        output_path = self.output_dir / "sb_winners_combined.csv"
        if output_path.exists():
            logger.info(f"[SKIP] {output_path} already exists")
            return pd.read_csv(output_path)

        perf = self.load_performance_data()
        contracts = self.load_contract_data(["KC", "TB", "PHI"])
        merged = self.merge(perf, contracts)
        merged.to_csv(output_path, index=False)
        logger.info(f"Saved SB winners roster ({len(merged)} players) to {output_path}")
        return merged
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
conda run -n nfl_analytics pytest tests/test_roster_builder.py -v
```

Expected:
```
PASSED tests/test_roster_builder.py::test_epa_weighted_decay_three_seasons
PASSED tests/test_roster_builder.py::test_epa_prorated_when_seasons_missing
PASSED tests/test_roster_builder.py::test_games_missed_raw_sum
PASSED tests/test_roster_builder.py::test_snaps_raw_sum
PASSED tests/test_roster_builder.py::test_merge_exact_match
PASSED tests/test_roster_builder.py::test_unmatched_player_included_with_nulls
PASSED tests/test_roster_builder.py::test_unmatched_log_written
7 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/data_collection/roster_builder.py tests/test_roster_builder.py
git commit -m "feat: add RosterBuilder with weighted EPA aggregation and fuzzy merge"
```

---

### Task 4: Build DataProcessor (Stage 4)

**Files:**
- Create: `tests/test_data_processor.py`
- Create: `src/data_collection/data_processor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_data_processor.py`:

```python
import pytest
import pandas as pd
import numpy as np
from src.data_collection.data_processor import DataProcessor
from src.player_valuation import PlayerAsset


@pytest.fixture
def sample_merged() -> pd.DataFrame:
    """Simulates output of RosterBuilder.merge() — mixed matched/unmatched."""
    return pd.DataFrame([
        {
            "player_name": "George Kittle", "position": "TE", "team": "SF", "age": 31,
            "cap_hit": 10_900_000.0, "total_value": 75_000_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 12.9, "snaps_played": 2400, "games_missed": 4,
        },
        {
            "player_name": "Brandon Aiyuk", "position": "WR", "team": "SF", "age": 27,
            "cap_hit": 24_900_000.0, "total_value": 120_000_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": np.nan, "snaps_played": np.nan, "games_missed": np.nan,
        },
        {
            "player_name": "Brock Purdy", "position": "QB", "team": "SF", "age": 26,
            "cap_hit": 37_750_000.0, "total_value": 244_200_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 35.0, "snaps_played": 2050, "games_missed": 0,
        },
    ])


def test_compute_features_fills_null_epa_with_positional_average(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    aiyuk = result[result["player_name"] == "Brandon Aiyuk"].iloc[0]
    # WR positional average from Kittle (TE doesn't count) — only Purdy (QB)
    # but Aiyuk is WR and Purdy is QB, no WR average available → falls back to global avg
    assert not pd.isna(aiyuk["epa_total"])


def test_compute_features_does_not_alter_matched_players(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    kittle = result[result["player_name"] == "George Kittle"].iloc[0]
    assert kittle["epa_total"] == 12.9
    assert kittle["snaps_played"] == 2400
    assert kittle["games_missed"] == 4


def test_enforce_schema_renames_columns(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    result = processor.enforce_schema(filled)
    assert "cap_hit_2026" in result.columns
    assert "total_contract_value" in result.columns
    assert "name" in result.columns
    assert "cap_hit" not in result.columns
    assert "total_value" not in result.columns
    assert "player_name" not in result.columns


def test_enforce_schema_generates_player_id(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    result = processor.enforce_schema(filled)
    assert "player_id" in result.columns
    assert result["player_id"].notna().all()


def test_to_player_assets_returns_list_of_player_assets(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    schemed = processor.enforce_schema(filled)
    assets = processor.to_player_assets(schemed)
    assert isinstance(assets, list)
    assert all(isinstance(a, PlayerAsset) for a in assets)
    assert len(assets) == 3


def test_to_player_assets_fields_are_correct_types(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    schemed = processor.enforce_schema(filled)
    assets = processor.to_player_assets(schemed)
    purdy = next(a for a in assets if "Purdy" in a.name)
    assert isinstance(purdy.cap_hit_2026, float)
    assert isinstance(purdy.age, int)
    assert isinstance(purdy.snaps_played, int)
    assert isinstance(purdy.games_missed, int)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_data_processor.py -v
```

Expected: all fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement DataProcessor**

Create `src/data_collection/data_processor.py`:

```python
import logging
import re
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

VALID_POSITIONS = {
    "QB", "WR", "RB", "TE", "OT", "OG", "C",
    "EDGE", "DL", "LB", "CB", "S", "K", "P", "LS",
}

COLUMN_RENAME = {
    "player_name": "name",
    "cap_hit":     "cap_hit_2026",
    "total_value": "total_contract_value",
}

REQUIRED_ASSET_FIELDS = [
    "player_id", "name", "position", "team", "age",
    "cap_hit_2026", "years_remaining", "guaranteed_money",
    "total_contract_value", "epa_total", "snaps_played", "games_missed",
]


def _make_player_id(row: pd.Series) -> str:
    """Generate a deterministic player_id from team + name."""
    name_slug = re.sub(r"[^a-z0-9]", "_", str(row.get("name", "")).lower())
    team = str(row.get("team", "unk")).lower()
    return f"{team}_{name_slug}"


class DataProcessor:
    """Feature engineering and PlayerAsset schema enforcement for merged roster data."""

    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_merged_data(self, path: str) -> pd.DataFrame:
        """Load a merged roster CSV (output of RosterBuilder).

        Args:
            path: Path to nfc_west_rosters.csv or sb_winners_combined.csv.

        Returns:
            Loaded DataFrame.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"{p} not found. Run Stage 3 first: "
                "python collect_all_data.py --force-stage merge"
            )
        df = pd.read_csv(p)
        logger.info(f"Loaded {len(df)} players from {p}")
        return df

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill null performance fields with per-position averages from matched players.

        Players that were unmatched in the fuzzy merge have NaN for epa_total,
        snaps_played, and games_missed. Fill them using the positional average
        computed from matched players in the same dataset. If no positional
        average exists (position has zero matched players), fall back to the
        global average across all positions.

        Args:
            df: Output of RosterBuilder.merge() — one row per player.

        Returns:
            DataFrame with no null values in epa_total, snaps_played, games_missed.
        """
        df = df.copy()
        perf_cols = ["epa_total", "snaps_played", "games_missed"]

        for col in perf_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Compute positional averages from matched (non-null) players
        pos_averages = (
            df[df["epa_total"].notna()]
            .groupby("position")[perf_cols]
            .mean()
        )
        global_averages = df[df["epa_total"].notna()][perf_cols].mean()

        for idx, row in df.iterrows():
            if pd.isna(row.get("epa_total")):
                pos = str(row.get("position", "")).upper()
                for col in perf_cols:
                    if pos in pos_averages.index:
                        df.at[idx, col] = pos_averages.loc[pos, col]
                    else:
                        df.at[idx, col] = global_averages[col]

        return df

    def enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns to match PlayerAsset field names and coerce types.

        Args:
            df: Output of compute_features().

        Returns:
            DataFrame with exact PlayerAsset column names and correct types.
        """
        df = df.copy()
        df = df.rename(columns=COLUMN_RENAME)

        # Generate player_id if missing
        if "player_id" not in df.columns:
            df["player_id"] = df.apply(_make_player_id, axis=1)

        # Ensure all required fields exist
        for field in REQUIRED_ASSET_FIELDS:
            if field not in df.columns:
                logger.warning(f"Missing field '{field}' — defaulting to 0")
                df[field] = 0

        # Coerce types
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(25).astype(int)
        df["years_remaining"] = pd.to_numeric(
            df["years_remaining"], errors="coerce"
        ).fillna(1).astype(int)
        df["snaps_played"] = pd.to_numeric(
            df["snaps_played"], errors="coerce"
        ).fillna(0).astype(int)
        df["games_missed"] = pd.to_numeric(
            df["games_missed"], errors="coerce"
        ).fillna(0).astype(int)

        for col in ["cap_hit_2026", "total_contract_value",
                    "guaranteed_money", "epa_total"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        # Normalize position to uppercase
        df["position"] = df["position"].str.upper().str.strip()

        return df

    def to_player_assets(self, df: pd.DataFrame) -> List[PlayerAsset]:
        """Instantiate PlayerAsset objects from a schema-enforced DataFrame.

        Args:
            df: Output of enforce_schema().

        Returns:
            List of PlayerAsset instances ready for PlayerValuationModel.value_roster().
        """
        assets = []
        for _, row in df.iterrows():
            try:
                assets.append(PlayerAsset(
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
                ))
            except Exception as e:
                logger.warning(f"Skipping player {row.get('name', '?')}: {e}")
        return assets

    def process(self, merged_path: str) -> pd.DataFrame:
        """Full Stage 4: load → compute features → enforce schema → save.

        Args:
            merged_path: Path to nfc_west_rosters.csv or sb_winners_combined.csv.

        Returns:
            Schema-enforced DataFrame saved to data/processed/player_assets_ready.csv.
        """
        output_path = self.output_dir / "player_assets_ready.csv"
        if output_path.exists():
            logger.info(f"[SKIP] {output_path} already exists")
            return pd.read_csv(output_path)

        df = self.load_merged_data(merged_path)
        df = self.compute_features(df)
        df = self.enforce_schema(df)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} PlayerAsset-ready rows to {output_path}")
        return df
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
conda run -n nfl_analytics pytest tests/test_data_processor.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/data_collection/data_processor.py tests/test_data_processor.py
git commit -m "feat: add DataProcessor with positional averaging and PlayerAsset schema"
```

---

### Task 5: Build `collect_all_data.py` orchestrator

**Files:**
- Create: `collect_all_data.py`
- Modify: `src/data_collection/__init__.py`

- [ ] **Step 1: Update `src/data_collection/__init__.py`**

Replace contents of `src/data_collection/__init__.py`:

```python
from src.data_collection.nflfastr_collection import NFLDataCollector
from src.data_collection.overthecap_scraper import OverTheCapScraper
from src.data_collection.roster_builder import RosterBuilder
from src.data_collection.data_processor import DataProcessor
```

- [ ] **Step 2: Create `collect_all_data.py`**

```python
"""Master data collection pipeline.

Usage:
    python collect_all_data.py                          # full run, skips cached stages
    python collect_all_data.py --force-stage contracts  # re-run OTC scraping only
    python collect_all_data.py --force-stage merge      # re-run merge only
    python collect_all_data.py --force-stage features   # re-run feature engineering only
    python collect_all_data.py --force-stage validate   # re-run validation only
    python collect_all_data.py --force-all              # ignore all cached outputs
"""
import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.data_collection.nflfastr_collection import NFLDataCollector
from src.data_collection.overthecap_scraper import OverTheCapScraper
from src.data_collection.roster_builder import RosterBuilder
from src.data_collection.data_processor import DataProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

YEARS = [2023, 2024, 2025]

VALID_POSITIONS = {
    "QB", "WR", "RB", "TE", "OT", "OG", "C",
    "EDGE", "DL", "LB", "CB", "S", "K", "P", "LS",
}

PERFORMANCE_FILES = [
    Path("data/raw/performance/pbp_2023_2025.parquet"),
    Path("data/raw/performance/player_stats_2023_2025.csv"),
    Path("data/raw/performance/rosters_2023_2025.csv"),
    Path("data/raw/performance/injuries_2023_2025.csv"),
]

CONTRACT_FILES = [
    Path("data/raw/contracts/sf_2026.csv"),
    Path("data/raw/contracts/sea_2026.csv"),
    Path("data/raw/contracts/lar_2026.csv"),
    Path("data/raw/contracts/ari_2026.csv"),
    Path("data/raw/contracts/sb_winners/kc_2026.csv"),
    Path("data/raw/contracts/sb_winners/tb_2026.csv"),
    Path("data/raw/contracts/sb_winners/phi_2026.csv"),
]


def _section(title: str) -> None:
    logger.info("=" * 55)
    logger.info(f"  {title}")
    logger.info("=" * 55)


def run_stage_performance(force: bool = False) -> None:
    _section("Stage 1: Performance Data Collection")
    if not force and all(f.exists() for f in PERFORMANCE_FILES):
        logger.info("[SKIP] All performance files already exist")
        return
    collector = NFLDataCollector()
    collector.collect_all(YEARS)


def run_stage_contracts(force: bool = False) -> None:
    _section("Stage 2: OTC Contract Scraping")
    if not force and all(f.exists() for f in CONTRACT_FILES):
        logger.info("[SKIP] All contract files already exist")
        return
    scraper = OverTheCapScraper()
    results = scraper.scrape_all()
    logger.info(f"Scraped {len(results)} teams: {list(results.keys())}")


def run_stage_merge(force: bool = False) -> None:
    _section("Stage 3: Roster Building + Fuzzy Merge")
    nfc_path = Path("data/processed/nfc_west_rosters.csv")
    sb_path = Path("data/processed/sb_winners_combined.csv")
    if not force and nfc_path.exists() and sb_path.exists():
        logger.info("[SKIP] Merged roster files already exist")
        return
    if force:
        nfc_path.unlink(missing_ok=True)
        sb_path.unlink(missing_ok=True)
    builder = RosterBuilder()
    nfc = builder.build_nfc_west()
    sb = builder.build_sb_winners()
    logger.info(f"NFC West: {len(nfc)} players | SB Winners: {len(sb)} players")


def run_stage_features(force: bool = False) -> None:
    _section("Stage 4: Feature Engineering")
    output_path = Path("data/processed/player_assets_ready.csv")
    if not force and output_path.exists():
        logger.info("[SKIP] player_assets_ready.csv already exists")
        return
    if force:
        output_path.unlink(missing_ok=True)
    processor = DataProcessor()
    processor.process("data/processed/nfc_west_rosters.csv")


def run_stage_validate() -> None:
    _section("Stage 5: Validation")
    path = Path("data/processed/player_assets_ready.csv")
    if not path.exists():
        logger.error("player_assets_ready.csv not found — run earlier stages first.")
        sys.exit(1)

    df = pd.read_csv(path)
    errors = []

    # Required fields present
    required = [
        "player_id", "name", "position", "team", "age",
        "cap_hit_2026", "years_remaining", "guaranteed_money",
        "total_contract_value", "epa_total", "snaps_played", "games_missed",
    ]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    # No nulls in critical numeric fields
    critical_numeric = ["cap_hit_2026", "epa_total", "snaps_played", "games_missed"]
    for col in critical_numeric:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append(f"{col} has {null_count} null values")

    # Valid positions
    if "position" in df.columns:
        invalid_pos = set(df["position"].str.upper().unique()) - VALID_POSITIONS
        if invalid_pos:
            errors.append(f"Invalid positions: {invalid_pos}")

    # cap_hit_2026 > 0
    if "cap_hit_2026" in df.columns:
        zero_cap = (df["cap_hit_2026"] <= 0).sum()
        if zero_cap > 0:
            errors.append(f"{zero_cap} players have cap_hit_2026 <= 0")

    # Age bounds
    if "age" in df.columns:
        out_of_range = ((df["age"] < 18) | (df["age"] > 45)).sum()
        if out_of_range > 0:
            errors.append(f"{out_of_range} players have age outside 18-45")

    # ---- Summary report ----
    logger.info("-" * 55)
    logger.info("VALIDATION SUMMARY")
    logger.info("-" * 55)
    logger.info(f"Total players:          {len(df)}")

    if "team" in df.columns:
        for team, count in df["team"].value_counts().items():
            logger.info(f"  {team:<6}: {count} players")

    if "epa_total" in df.columns and len(df) > 0:
        matched = df["epa_total"].notna().sum()
        logger.info(f"Fuzzy match rate:       {matched}/{len(df)} "
                    f"({matched/len(df)*100:.1f}%)")

    unmatched_path = Path("data/processed/unmatched_players.csv")
    if unmatched_path.exists():
        unmatched_df = pd.read_csv(unmatched_path)
        logger.info(f"Unmatched players:      {len(unmatched_df)} "
                    f"(see {unmatched_path})")

    if errors:
        logger.error("VALIDATION FAILED:")
        for e in errors:
            logger.error(f"  ✗ {e}")
        sys.exit(1)
    else:
        logger.info("All validation checks passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL Data Collection Pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--force-stage",
        choices=["performance", "contracts", "merge", "features", "validate"],
        help="Force re-run of a specific stage",
    )
    group.add_argument(
        "--force-all", action="store_true",
        help="Force full re-run, ignoring all cached outputs",
    )
    args = parser.parse_args()

    force_all = args.force_all
    force_stage = args.force_stage

    run_stage_performance(force=force_all or force_stage == "performance")
    run_stage_contracts(force=force_all or force_stage == "contracts")
    run_stage_merge(force=force_all or force_stage == "merge")
    run_stage_features(force=force_all or force_stage == "features")
    run_stage_validate()

    _section("Pipeline Complete")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add collect_all_data.py src/data_collection/__init__.py
git commit -m "feat: add collect_all_data.py orchestrator with stage resumability"
```

---

### Task 6: Run the full pipeline and validate

- [ ] **Step 1: Run the full pipeline**

```bash
conda run -n nfl_analytics python collect_all_data.py
```

Stage 1 (performance data) will take 5-15 minutes on first run. Stages 2-5 follow automatically.

- [ ] **Step 2: If Stage 2 fails (OTC HTML structure changed)**

If any team returns an empty DataFrame, inspect the live page:

```bash
conda run -n nfl_analytics python -c "
import requests, pandas as pd
r = requests.get('https://overthecap.com/roster/san-francisco-49ers',
    headers={'User-Agent': 'Mozilla/5.0'})
tables = pd.read_html(r.text)
print(f'Found {len(tables)} tables')
for i, t in enumerate(tables):
    print(f'Table {i}: shape={t.shape}, cols={list(t.columns[:8])}')
"
```

Update the `col_map` in `_parse_roster_html` to match the actual column names found, then re-run:

```bash
conda run -n nfl_analytics python collect_all_data.py --force-stage contracts
```

- [ ] **Step 3: If Stage 3 fuzzy match rate is low (<80%)**

Inspect the unmatched players:

```bash
conda run -n nfl_analytics python -c "
import pandas as pd
df = pd.read_csv('data/processed/unmatched_players.csv')
print(df.sort_values('match_score', ascending=False).to_string())
"
```

Common causes:
- Position mismatch: OTC uses "DE" while nfl_data_py uses "EDGE" → add to `TEAM_NORMALIZER` or add a position normalizer map in `RosterBuilder`
- Name format differences: update `_normalize_name` regex

- [ ] **Step 4: Review validation output**

After a successful run, the pipeline prints a summary like:
```
Total players:          220
  SF    : 53 players
  SEA   : 53 players
  LAR   : 53 players
  ARI   : 53 players
  ...
Fuzzy match rate:       198/220 (90.0%)
Unmatched players:      22 (see data/processed/unmatched_players.csv)
All validation checks passed.
```

- [ ] **Step 5: Run full test suite**

```bash
conda run -n nfl_analytics pytest tests/ -v
```

Expected: all previously written tests pass.

- [ ] **Step 6: Final commit**

```bash
git add data/processed/unmatched_players.csv
git commit -m "feat: run data collection pipeline, all stages pass validation"
```

---

## Self-Review Notes

- **Spec § Stage 1:** Covered by Task 1 — NFLDataCollector already built, Stage 1 run in Task 1 Step 2. ✓
- **Spec § Stage 2:** Covered by Task 2 — all 7 team files, 2s rate limit, skip if exists, SF/ARI added to TEAM_SLUGS. ✓
- **Spec § Stage 3:** Covered by Task 3 — weighted EPA, raw snaps/games, fuzzy merge at 85 threshold, unmatched CSV with correct columns. ✓
- **Spec § Stage 4:** Covered by Task 4 — positional average fill from matched players, schema rename, `to_player_assets`. ✓
- **Spec § Stage 5:** Covered by Task 5 (orchestrator) — all 5 validation checks, summary report. ✓
- **Spec § Orchestrator:** Covered by Task 5 — all `--force-stage` options plus `--force-all`. ✓
- **Key constraints:** Absolute imports used throughout. Rate limit (2s) enforced in `scrape_team`. Google-style docstrings and type hints in all new files. ✓
