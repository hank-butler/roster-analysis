"""RosterBuilder: Aggregates nfl_data_py performance stats and fuzzy-merges with OTC contract data."""

import re
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

EPA_WEIGHTS = {2025: 0.5, 2024: 0.3, 2023: 0.2}
FUZZY_THRESHOLD = 85
GAMES_PER_SEASON = 17

TEAM_NORMALIZER = {
    "LA": "LAR",
    "OAK": "LV",
}


def _normalize_team(team: str) -> str:
    """Normalize team abbreviation to a standard form."""
    t = str(team).upper().strip()
    return TEAM_NORMALIZER.get(t, t)


def _normalize_name(name: str) -> str:
    """Lowercase, remove name suffixes and punctuation for fuzzy matching."""
    name = str(name).lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    return " ".join(name.split())


class RosterBuilder:
    """Aggregates nfl_data_py performance stats and fuzzy-merges with OTC contract data."""

    def __init__(
        self,
        perf_dir: str = "data/raw/performance",
        contract_dir: str = "data/raw/contracts",
        output_dir: str = "data/processed",
    ):
        self.perf_dir = Path(perf_dir)
        self.contract_dir = Path(contract_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _aggregate_performance(
        self, stats_df: pd.DataFrame, rosters_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Join stats + roster data and aggregate across seasons per player.

        EPA uses weighted decay (2025: 50%, 2024: 30%, 2023: 20%), prorated
        when a player is missing some seasons. Snaps and games_missed are raw
        3-season sums to preserve the valuation model's denominator assumptions.

        Args:
            stats_df: From nfl_data_py.import_seasonal_data — player_id, season,
                      games, passing_epa, rushing_epa, receiving_epa, offense_snaps
                      (no player_name or team).
            rosters_df: From nfl_data_py.import_seasonal_rosters — player_id, season,
                        player_name, position, team.

        Returns:
            DataFrame with one row per player: player_name, team, position,
            epa_total, snaps_played, games_missed.
        """
        # Join stats to rosters to get player_name, position, team
        rosters_slim = rosters_df[
            ["player_id", "season", "player_name", "position", "team"]
        ].drop_duplicates(subset=["player_id", "season"])

        df = stats_df.merge(rosters_slim, on=["player_id", "season"], how="inner")
        if df.empty:
            raise ValueError(
                "Performance/roster join produced 0 rows. Verify that player_id and season "
                "columns exist in both inputs and cover overlapping seasons."
            )
        df["team"] = df["team"].apply(_normalize_team)

        # Total EPA per player-season
        epa_cols = [c for c in ["passing_epa", "rushing_epa", "receiving_epa"]
                    if c in df.columns]
        if epa_cols:
            df["season_epa"] = df[epa_cols].fillna(0).sum(axis=1)
        else:
            df["season_epa"] = 0.0

        # Snaps per player-season
        snap_cols = [c for c in ["offense_snaps", "defense_snaps"] if c in df.columns]
        if snap_cols:
            df["season_snaps"] = df[snap_cols].fillna(0).sum(axis=1)
        else:
            df["season_snaps"] = df.get("games", pd.Series(0, index=df.index)).fillna(0) * 65
            logger.warning("No snap columns found — using games * 65 as proxy")

        df["season_games_missed"] = (GAMES_PER_SEASON - df["games"].fillna(0)).clip(lower=0)

        records = []
        for (player_name, team, position), group in df.groupby(
            ["player_name", "team", "position"]
        ):
            available_weights = {
                yr: w for yr, w in EPA_WEIGHTS.items() if yr in group["season"].values
            }
            total_weight = sum(available_weights.values())
            if total_weight == 0:
                epa_total = 0.0
            else:
                epa_total = sum(
                    group.loc[group["season"] == yr, "season_epa"].sum() * (w / total_weight)
                    for yr, w in available_weights.items()
                )

            records.append({
                "player_name": player_name,
                "team": team,
                "position": position,
                "epa_total": round(epa_total, 4),
                "snaps_played": int(group["season_snaps"].sum()),
                "games_missed": int(group["season_games_missed"].sum()),
            })

        return pd.DataFrame(records)

    def load_performance_data(self) -> pd.DataFrame:
        """Load and aggregate performance data from Stage 1 CSVs.

        Returns:
            Aggregated per-player DataFrame with epa_total, snaps_played, games_missed.

        Raises:
            FileNotFoundError: If Stage 1 CSVs are missing.
        """
        stats_path = self.perf_dir / "player_stats_2023_2025.csv"
        rosters_path = self.perf_dir / "rosters_2023_2025.csv"
        for p in (stats_path, rosters_path):
            if not p.exists():
                raise FileNotFoundError(
                    f"{p} not found. Run Stage 1 first: "
                    "python collect_all_data.py --force-stage performance"
                )
        stats_df = pd.read_csv(stats_path)
        rosters_df = pd.read_csv(rosters_path)
        logger.info(f"Loaded {len(stats_df)} stat rows and {len(rosters_df)} roster rows")
        return self._aggregate_performance(stats_df, rosters_df)

    def load_contract_data(self, teams: List[str]) -> pd.DataFrame:
        """Load OTC contract CSVs for the given team abbreviations.

        Args:
            teams: List of team abbreviations (e.g., ['SF', 'SEA']).

        Returns:
            Combined contract DataFrame.

        Raises:
            FileNotFoundError: If no contract CSVs are found.
        """
        frames = []
        sb_teams = {"KC", "TB", "PHI"}
        for team in teams:
            if team in sb_teams:
                path = self.contract_dir / "sb_winners" / f"{team.lower()}_2026.csv"
            else:
                path = self.contract_dir / f"{team.lower()}_2026.csv"
            if not path.exists():
                logger.warning(f"[{team}] Contract file not found: {path}. Skipping.")
                continue
            frames.append(pd.read_csv(path))

        if not frames:
            raise FileNotFoundError(
                "No contract CSVs found. Run Stage 2 first: "
                "python collect_all_data.py --force-stage contracts"
            )
        return pd.concat(frames, ignore_index=True)

    def merge(
        self, perf_df: pd.DataFrame, contract_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Fuzzy-merge performance stats onto OTC contract rows.

        Matches on normalized player name + team (not position, since OTC data
        lacks reliable position info). Matched rows get performance columns
        populated; unmatched rows remain with NaN performance fields and are
        logged to unmatched_players.csv.

        Args:
            perf_df: Output of _aggregate_performance().
            contract_df: Loaded OTC contract DataFrame.

        Returns:
            Merged DataFrame with one row per OTC player.
        """
        perf = perf_df.copy()
        contracts = contract_df.copy()

        perf["_norm_name"] = perf["player_name"].apply(_normalize_name)
        perf["_norm_team"] = perf["team"].apply(_normalize_team)
        contracts["_norm_name"] = contracts["player_name"].apply(_normalize_name)
        contracts["_norm_team"] = contracts["team"].apply(_normalize_team)

        perf_cols = ["epa_total", "snaps_played", "games_missed"]
        matched_rows = []
        unmatched_rows = []

        for _, otc_row in contracts.iterrows():
            otc_name = otc_row["_norm_name"]
            otc_team = otc_row["_norm_team"]

            # Match on team only (position unreliable from OTC)
            candidates = perf[perf["_norm_team"] == otc_team]

            best_score, best_match = 0, None
            for _, perf_row in candidates.iterrows():
                score = fuzz.token_sort_ratio(otc_name, perf_row["_norm_name"])
                if score > best_score:
                    best_score, best_match = score, perf_row

            row_dict = otc_row.drop(labels=["_norm_name", "_norm_team"]).to_dict()

            if best_match is not None and best_score >= FUZZY_THRESHOLD:
                for col in perf_cols:
                    row_dict[col] = best_match[col]
                # Backfill position from nfl_data_py if OTC position is null
                if pd.isna(row_dict.get("position")):
                    row_dict["position"] = best_match.get("position", "")
            else:
                for col in perf_cols:
                    row_dict[col] = np.nan
                unmatched_rows.append({
                    "otc_name": otc_row["player_name"],
                    "otc_team": otc_row.get("team", ""),
                    "otc_position": otc_row.get("position", ""),
                    "nfl_name": best_match["player_name"] if best_match is not None else "",
                    "nfl_team": best_match["team"] if best_match is not None else "",
                    "nfl_position": best_match["position"] if best_match is not None else "",
                    "match_score": best_score,
                })

            matched_rows.append(row_dict)

        merged_df = pd.DataFrame(matched_rows)

        total = len(contracts)
        matched_count = total - len(unmatched_rows)
        match_pct = matched_count / total * 100 if total > 0 else 0
        logger.info(f"Fuzzy match rate: {matched_count}/{total} ({match_pct:.1f}%)")
        if match_pct < 50:
            logger.warning(
                f"Match rate below 50% — check team normalization and name formats. "
                f"Top unmatched scores: {sorted([r['match_score'] for r in unmatched_rows], reverse=True)[:5]}"
            )

        unmatched_path = self.output_dir / "unmatched_players.csv"
        unmatched_frame = pd.DataFrame(
            unmatched_rows if unmatched_rows else [],
            columns=["otc_name", "otc_team", "otc_position",
                     "nfl_name", "nfl_team", "nfl_position", "match_score"],
        )
        unmatched_frame.to_csv(unmatched_path, index=False)
        if unmatched_rows:
            logger.info(f"{len(unmatched_rows)} unmatched players → {unmatched_path}")

        return merged_df.drop(columns=["_norm_name", "_norm_team"], errors="ignore")

    def build_nfc_west(self) -> pd.DataFrame:
        """Build and save nfc_west_rosters.csv.

        Returns:
            Merged DataFrame for SF, SEA, LAR, ARI.
        """
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
        """Build and save sb_winners_combined.csv.

        Returns:
            Merged DataFrame for KC, TB, PHI.
        """
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
