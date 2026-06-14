import nfl_data_py as nfl
import pandas as pd
import requests
from pathlib import Path
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NFLDataCollector:
    """
    Collects performance data from nflfastR package
    """

    def __init__(self, output_dir: str = "data/raw/performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_play_by_play(self, years: List[int]) -> pd.DataFrame:
        """
        Collect play by play data with EPA

        args:
        years: int

        returns:
        pandas dataframe
        """

        logger.info(f"Collecting play-by-play data for {years}")

        frames = []
        for year in years:
            try:
                df = nfl.import_pbp_data([year])
                frames.append(df)
                logger.info(f"  Collected play-by-play for {year}: {len(df):,} plays")
            except (KeyError, ValueError, requests.exceptions.HTTPError) as e:
                logger.warning(f"  Skipping {year} play-by-play data (not yet available): {e}")

        if not frames:
            raise RuntimeError(f"No play-by-play data available for any of {years}")

        pbp = pd.concat(frames, ignore_index=True)

        # save the data files to the data folder
        output_path = self.output_dir / f"pbp_{min(years)}_{max(years)}.parquet"
        pbp.to_parquet(output_path)
        logger.info(f"Saved {len(pbp):,} plays to {output_path}")

        return pbp
    
    def collect_player_stats(self, years: List[int]) -> pd.DataFrame:
        """
        Collect seasonal player stats.

        ARGS:
        years: list of ints

        RETURNS:
        pandas DataFrame
        """
        logger.info(f"Collecting player stats for {years}")

        # Some years may not yet have seasonal data published (e.g. current/future
        # seasons). Collect available years and skip those that return 404.
        frames = []
        for year in years:
            try:
                df = nfl.import_seasonal_data([year])
                frames.append(df)
                logger.info(f"  Collected stats for {year}: {len(df):,} player-seasons")
            except (KeyError, ValueError, requests.exceptions.HTTPError) as e:
                logger.warning(f"  Skipping {year} seasonal stats (not yet available): {e}")

        if not frames:
            raise RuntimeError(f"No seasonal stats available for any of {years}")

        stats = pd.concat(frames, ignore_index=True)

        # Save
        output_path = self.output_dir / f"player_stats_{min(years)}_{max(years)}.csv"
        stats.to_csv(output_path, index=False)
        logger.info(f"Saved stats for {len(stats):,} player-seasons to {output_path}")

        return stats
    
    def collect_rosters(self, years: List[int]) -> pd.DataFrame:
        """
        Collect roster data (age, position, draft info)

        ARGS:
        years: List of int

        RETURNS:
        pandas DataFrame
        """
        logger.info(f"Collecting roster data for {years}...")

        frames = []
        for year in years:
            try:
                df = nfl.import_seasonal_rosters([year])
                frames.append(df)
                logger.info(f"  Collected rosters for {year}: {len(df):,} entries")
            except (KeyError, ValueError, requests.exceptions.HTTPError) as e:
                logger.warning(f"  Skipping {year} roster data (not yet available): {e}")

        if not frames:
            raise RuntimeError(f"No roster data available for any of {years}")

        rosters = pd.concat(frames, ignore_index=True)

        # Save, specify output path
        output_path = self.output_dir / f"rosters_{min(years)}_{max(years)}.csv"
        rosters.to_csv(output_path, index=False)
        logger.info(f"Saved {len(rosters):,} roster entries to {output_path}")

        return rosters
    
    def collect_injuries(self, years: List[int]) -> pd.DataFrame:
        """
        Injury data on players

        ARGS:
        years: List[ints]

        RETURNS:
        pandas DataFrame
        """

        logger.info(f"Collecting injury data for {years}...")

        frames = []
        for year in years:
            try:
                df = nfl.import_injuries([year])
                frames.append(df)
                logger.info(f"  Collected injury data for {year}: {len(df):,} reports")
            except (KeyError, ValueError, requests.exceptions.HTTPError) as e:
                logger.warning(f"  Skipping {year} injury data (not yet available): {e}")

        if not frames:
            raise RuntimeError(f"No injury data available for any of {years}")

        injuries = pd.concat(frames, ignore_index=True)

        # Save and export
        output_path = self.output_dir / f"injuries_{min(years)}_{max(years)}.csv"
        injuries.to_csv(output_path, index=False)
        logger.info(f"Saved {len(injuries):,} injury reports to {output_path}")

        return injuries
    
    def collect_all(self, years: List[int]=[2023, 2024, 2025]) -> dict:
        """
        ARGS:
        years: List[int], defaulted to 2023, 2024, 2025
        
        RETURNS:
        dict: 
            keys: data subsets (pbp, stats, injuries, rosters)
            values: pandas DataFrames
        """
        logger.info("="*50)
        logger.info("COLLECTING ALL NFL PERFORMANCE DATA")
        logger.info("="*50)

        data = {
            "pbp": self.collect_play_by_play(years),
            "stats": self.collect_player_stats(years),
            "injuries": self.collect_injuries(years),
            "rosters": self.collect_rosters(years)
        }

        logger.info("All performance data collected successfully")

        return data


if __name__ == "__main__":
    collector = NFLDataCollector()
    data = collector.collect_all()

    print("\n" + "="*50)
    print("COLLECTION SUMMARY")
    print("="*50)
    print(f"Play-by-play records: {len(data['pbp']):,}")
    print(f"Player stat records: {len(data['stats']):,}")
    print(f"Player Injury records: {len(data['injuries']):,}")
    print(f"Roster records: {len(data['rosters']):,}")