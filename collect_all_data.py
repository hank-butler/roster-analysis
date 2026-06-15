"""Master data collection pipeline.

Usage:
    python collect_all_data.py                           # full run, skips cached stages
    python collect_all_data.py --force-stage performance # re-run performance data only
    python collect_all_data.py --force-stage contracts   # re-run OTC scraping only
    python collect_all_data.py --force-stage merge       # re-run merge only
    python collect_all_data.py --force-stage features    # re-run feature engineering only
    python collect_all_data.py --force-stage validate    # re-run validation only
    python collect_all_data.py --force-all               # ignore all cached outputs
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
    # Composite designations used by nfl_data_py / OverTheCap
    "DB", "OL", "DL", "FL", "NT", "DE", "ILB", "OLB", "SAF", "NCB",
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
    """Stage 1: Download NFL performance data via nfl_data_py."""
    _section("Stage 1: Performance Data Collection")
    if not force and all(f.exists() for f in PERFORMANCE_FILES):
        logger.info("[SKIP] All performance files already exist")
        return
    collector = NFLDataCollector()
    collector.collect_all(YEARS)


def run_stage_contracts(force: bool = False) -> None:
    """Stage 2: Scrape contract data from OverTheCap."""
    _section("Stage 2: OTC Contract Scraping")
    if not force and all(f.exists() for f in CONTRACT_FILES):
        logger.info("[SKIP] All contract files already exist")
        return
    scraper = OverTheCapScraper()
    results = scraper.scrape_all()
    logger.info(f"Scraped {len(results)} teams: {list(results.keys())}")


def run_stage_merge(force: bool = False) -> None:
    """Stage 3: Fuzzy-merge performance + contract data into roster CSVs."""
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
    """Stage 4: Feature engineering + PlayerAsset schema enforcement."""
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
    """Stage 5: Validate player_assets_ready.csv against PlayerAsset field requirements."""
    _section("Stage 5: Validation")
    path = Path("data/processed/player_assets_ready.csv")
    if not path.exists():
        logger.error("player_assets_ready.csv not found — run earlier stages first.")
        sys.exit(1)

    df = pd.read_csv(path)
    errors = []

    required = [
        "player_id", "name", "position", "team", "age",
        "cap_hit_2026", "years_remaining", "guaranteed_money",
        "total_contract_value", "epa_total", "snaps_played", "games_missed",
    ]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    critical_numeric = ["cap_hit_2026", "epa_total", "snaps_played", "games_missed"]
    for col in critical_numeric:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append(f"{col} has {null_count} null values")

    if "position" in df.columns:
        invalid_pos = set(df["position"].dropna().str.upper().unique()) - VALID_POSITIONS - {""}
        if invalid_pos:
            errors.append(f"Invalid positions found: {invalid_pos}")

    if "cap_hit_2026" in df.columns:
        zero_cap = (df["cap_hit_2026"] <= 0).sum()
        if zero_cap > 0:
            logger.warning(f"{zero_cap} players have cap_hit_2026 <= 0 (likely practice squad)")

    if "age" in df.columns:
        # Treat age == 0 as missing/not-yet-populated (DataProcessor may not calculate age)
        age_populated = df[df["age"] > 0]["age"]
        if len(age_populated) > 0:
            out_of_range = ((age_populated < 18) | (age_populated > 45)).sum()
            if out_of_range > 0:
                errors.append(f"{out_of_range} players have age outside 18-45")
        missing_age = (df["age"] == 0).sum()
        if missing_age > 0:
            logger.warning(f"{missing_age} players have age=0 (not yet populated by DataProcessor)")

    logger.info("-" * 55)
    logger.info("VALIDATION SUMMARY")
    logger.info("-" * 55)
    logger.info(f"Total players:       {len(df)}")

    if "team" in df.columns:
        for team, count in df["team"].value_counts().items():
            logger.info(f"  {team:<6}: {count} players")

    unmatched_path = Path("data/processed/unmatched_players.csv")
    if unmatched_path.exists():
        unmatched_df = pd.read_csv(unmatched_path)
        matched_count = len(df) - len(unmatched_df)
        match_pct = matched_count / len(df) * 100 if len(df) > 0 else 0
        logger.info(f"Fuzzy match rate:    {matched_count}/{len(df)} ({match_pct:.1f}%)")
        logger.info(f"Unmatched players:   {len(unmatched_df)} (see {unmatched_path})")

    if errors:
        logger.error("VALIDATION FAILED:")
        for e in errors:
            logger.error(f"  x {e}")
        sys.exit(1)
    else:
        logger.info("All validation checks passed")


def main() -> None:
    """Entry point for the data collection pipeline."""
    parser = argparse.ArgumentParser(description="NFL Data Collection Pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--force-stage",
        choices=["performance", "contracts", "merge", "features", "validate"],
        help="Force re-run of a specific stage, use cached outputs for all others",
    )
    group.add_argument(
        "--force-all",
        action="store_true",
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
