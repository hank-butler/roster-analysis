import nfl_data_py as nfl
import pandas as pd
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

        pbp = nfl.import_pbp_data(years)

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

        stats = nfl.import_seasonal_data(years)

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

        rosters = nfl.import_seasonal_rosters(years)

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

        injuries = nfl.import_injuries(years)

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
    print(f"Play-by-play records: {len(data['pbp']):, }")
    print(f"Player stat records: {len(data['stats']):,}")
    print(f"Player Injury records: {len(data['injuries']):,}")
    print(f"Roster records: {len(data['rosters']):,}")