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

    
