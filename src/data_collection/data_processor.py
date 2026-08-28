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
    """Generate a deterministic player_id from team + position + normalized name."""
    name_slug = re.sub(r"[^a-z0-9]", "_", str(row.get("name", "")).lower())
    team = str(row.get("team", "unk")).lower()
    pos = str(row.get("position", "unk")).lower()
    return f"{team}_{pos}_{name_slug}"


class DataProcessor:
    """Feature engineering and PlayerAsset schema enforcement for merged roster data."""

    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_merged_data(self, path: str) -> pd.DataFrame:
        """Load a merged roster CSV produced by RosterBuilder.

        Args:
            path: Path to afc_west_rosters.csv or sb_winners_combined.csv.

        Returns:
            Loaded DataFrame.

        Raises:
            FileNotFoundError: If the file does not exist.
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
        """Fill null performance fields using per-position averages from matched players.

        Players unmatched during fuzzy merge have NaN for epa_total, snaps_played,
        and games_missed. Fill them using the positional average computed from
        matched (non-null) players in the same dataset. If no matched players exist
        for a given position, fall back to the global average across all positions.

        Args:
            df: Output of RosterBuilder.merge() — one row per player, may have NaN
                performance fields for unmatched players.

        Returns:
            DataFrame with no null values in epa_total, snaps_played, games_missed.
        """
        df = df.copy()
        perf_cols = ["epa_total", "snaps_played", "games_missed"]

        for col in perf_cols:
            if col not in df.columns:
                df[col] = np.nan

        matched_mask = df["epa_total"].notna()

        # Per-position averages from matched players only
        pos_averages = (
            df[matched_mask]
            .groupby("position")[perf_cols]
            .mean()
        )
        global_averages = df[matched_mask][perf_cols].mean()

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
        """Rename columns to PlayerAsset field names and coerce to correct types.

        Args:
            df: Output of compute_features().

        Returns:
            DataFrame with exact PlayerAsset column names and correct Python types.
        """
        df = df.copy()
        df = df.rename(columns=COLUMN_RENAME)

        if "player_id" not in df.columns:
            df["player_id"] = df.apply(_make_player_id, axis=1)

        for field in REQUIRED_ASSET_FIELDS:
            if field not in df.columns:
                logger.warning(f"Missing field '{field}' — defaulting to 0")
                df[field] = 0

        # Treat age=0 as missing (OTC scraper stores 0 when age unavailable)
        df["age"] = pd.to_numeric(df["age"], errors="coerce").replace(0, np.nan).fillna(25).astype(int)
        df["years_remaining"] = (
            pd.to_numeric(df["years_remaining"], errors="coerce").fillna(1).astype(int)
        )
        df["snaps_played"] = (
            pd.to_numeric(df["snaps_played"], errors="coerce").fillna(0).astype(int)
        )
        df["games_missed"] = (
            pd.to_numeric(df["games_missed"], errors="coerce").fillna(0).astype(int)
        )
        for col in ["cap_hit_2026", "total_contract_value", "guaranteed_money", "epa_total"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df["position"] = df["position"].fillna("").astype(str).str.upper().str.strip()

        return df

    def to_player_assets(self, df: pd.DataFrame) -> List[PlayerAsset]:
        """Instantiate PlayerAsset objects from a schema-enforced DataFrame.

        Args:
            df: Output of enforce_schema().

        Returns:
            List of PlayerAsset instances ready for PlayerValuationModel.value_roster().
        """
        assets = []
        skip_count = 0
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
                skip_count += 1
                logger.warning(
                    f"Skipping player {row.get('name', '?')}: {e}", exc_info=True
                )
        if skip_count > 0:
            logger.warning(f"Skipped {skip_count} of {len(df)} players due to conversion errors")
        return assets

    def process(self, merged_path: str) -> pd.DataFrame:
        """Full Stage 4: load merged data -> compute features -> enforce schema -> save.

        Args:
            merged_path: Path to afc_west_rosters.csv or sb_winners_combined.csv.

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
