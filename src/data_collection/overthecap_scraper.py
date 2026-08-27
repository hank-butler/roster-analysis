import re
import time
import logging
from io import StringIO
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OverTheCapScraper:
    """Scrapes overthecap.com for team contract data."""

    BASE_URL = "https://overthecap.com/salary-cap/"

    TEAM_SLUGS = {
        "SF":  "san-francisco-49ers",
        "SEA": "seattle-seahawks",
        "LAR": "los-angeles-rams",
        "ARI": "arizona-cardinals",
        "DEN": "denver-broncos",
        "LAC": "los-angeles-chargers",
        "LV":  "las-vegas-raiders",
        "KC":  "kansas-city-chiefs",
        "TB":  "tampa-bay-buccaneers",
        "PHI": "philadelphia-eagles",
        "IND": "indianapolis-colts",
        "HOU": "houston-texans",
    }

    AFC_WEST = ["DEN", "KC", "LAC", "LV"]
    SB_WINNERS = ["KC", "TB", "PHI"]

    def __init__(self, output_dir: str = "data/raw/contracts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "sb_winners").mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    @staticmethod
    def _parse_currency(value: str) -> float:
        """Convert OTC currency string like '$37,750,000' to float."""
        if pd.isna(value):
            return 0.0
        cleaned = re.sub(r"[$,\s()]", "", str(value))
        if not cleaned or cleaned in ("—", "-", ""):
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _flatten_multiindex_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Collapse MultiIndex column headers into a single level."""
        if isinstance(df.columns, pd.MultiIndex):
            # Join levels, dropping duplicates like ('Player', 'Player') → 'player'
            new_cols = []
            for levels in df.columns:
                parts = [str(l).strip() for l in levels if not str(l).startswith("Unnamed")]
                # Deduplicate adjacent identical parts
                seen = []
                for p in parts:
                    if not seen or p != seen[-1]:
                        seen.append(p)
                new_cols.append(" ".join(seen).strip().lower())
            df.columns = new_cols
        else:
            df.columns = [str(c).lower().strip() for c in df.columns]
        return df

    def _parse_roster_html(self, html: str, team: str) -> pd.DataFrame:
        """Parse OTC salary-cap page HTML into a clean DataFrame.

        Handles both the original /roster/ table format (used in tests via
        the HTML fixture) and the current /salary-cap/ multi-level header
        format returned by the live site.

        Args:
            html: Raw HTML string from the OTC page.
            team: Team abbreviation to tag rows with (e.g., 'SF').

        Returns:
            DataFrame with columns: player_name, position, age, cap_hit,
            base_salary, total_value, dead_cap, team.
        """
        try:
            tables = pd.read_html(StringIO(html))
        except ValueError:
            logger.error(f"[{team}] No HTML tables found. First 500 chars: {html[:500]}")
            return pd.DataFrame()

        if not tables:
            logger.error(f"[{team}] pd.read_html returned empty list.")
            return pd.DataFrame()

        # Take the largest table (active roster on salary-cap pages)
        df = max(tables, key=len).copy()
        df = self._flatten_multiindex_columns(df)
        logger.info(f"[{team}] Largest table ({len(df)} rows), columns: {list(df.columns)}")

        # Unified column map — covers both fixture format and live OTC format.
        # Live /salary-cap/ page uses multi-level headers; after flattening:
        #   "prorated bonus signing" → signing_bonus
        #   "prorated bonus option"  → option_bonus
        #   "roster bonus regular"   → roster_bonus
        #   "cap number"             → cap_hit
        #   "guaranteed salary"      → guaranteed_money
        # "dead money & cap savings ..." columns → dead_cap (first one wins)
        col_map = {
            # Fixture / old /roster/ format
            "player": "player_name",
            "pos":    "position",
            "age":    "age",
            "base salary": "base_salary",
            "signing bonus": "signing_bonus",
            "cap hit": "cap_hit",
            "dead cap": "dead_cap",
            "total value": "total_value",
            "total": "total_value",
            "guaranteed": "guaranteed_money",
            # Live /salary-cap/ format (flattened multi-level)
            "cap number": "cap_hit",
            "guaranteed salary": "guaranteed_money",
            "prorated bonus signing": "signing_bonus",
            "prorated bonus option": "option_bonus",
            "roster bonus regular": "roster_bonus",
            "roster bonus per game": "per_game_bonus",
            "workout bonus": "workout_bonus",
            "other bonus": "other_bonus",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Map the first "dead money" column to dead_cap (the col name is very long)
        dead_cols = [c for c in df.columns if str(c).startswith("dead money")]
        if dead_cols and "dead_cap" not in df.columns:
            df = df.rename(columns={dead_cols[0]: "dead_cap"})

        # Drop remaining unnamed / verbose dead-money sub-columns
        drop_cols = [c for c in df.columns if c == "" or
                     (str(c).startswith("dead money") and c != "dead_cap")]
        df = df.drop(columns=drop_cols, errors="ignore")

        # Ensure all required columns exist
        for col in ["player_name", "position", "age", "cap_hit", "total_value",
                    "base_salary", "dead_cap", "guaranteed_money"]:
            if col not in df.columns:
                df[col] = 0 if col not in ("player_name", "position") else ""

        # Parse currency strings → float
        currency_cols = [
            "cap_hit", "base_salary", "total_value", "dead_cap", "guaranteed_money",
            "signing_bonus", "option_bonus", "roster_bonus", "per_game_bonus",
            "workout_bonus", "other_bonus",
        ]
        for col in currency_cols:
            if col in df.columns:
                df[col] = df[col].apply(self._parse_currency)

        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(0).astype(int)

        # Drop empty / header-repeat rows
        df = df[df["player_name"].astype(str).str.strip() != ""]
        df = df[df["player_name"].astype(str) != "nan"]
        # Drop rows where player_name looks like a column header repeat
        df = df[~df["player_name"].astype(str).str.lower().isin(["player", "name"])]

        df["team"] = team

        if "years_remaining" not in df.columns:
            df["years_remaining"] = 1

        return df.reset_index(drop=True)

    def _output_path(self, team: str) -> Path:
        """Return the output CSV path for a given team abbreviation."""
        if team in self.SB_WINNERS:
            return self.output_dir / "sb_winners" / f"{team.lower()}_2026.csv"
        return self.output_dir / f"{team.lower()}_2026.csv"

    def scrape_team(self, team: str) -> Optional[pd.DataFrame]:
        """Scrape one team's salary-cap page from OTC.

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

        time.sleep(2)
        return df

    def scrape_afc_west(self) -> Dict[str, pd.DataFrame]:
        """Scrape all 4 AFC West teams."""
        results = {}
        for team in self.AFC_WEST:
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
        results.update(self.scrape_afc_west())
        results.update(self.scrape_sb_winners())
        logger.info(f"Scraping complete. Teams collected: {list(results.keys())}")
        return results
