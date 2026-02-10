import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# print(logger)

class OverTheCapScraper:
    """
    Scrapes over the cap website to get up to date cap information.
    """
    BASE_URL = "https://overthecap.com/"

    TEAM_SLUGS = {
        "IND": 'indianapolis-colts',
        "HOU": 'houston-texans',
        "JAX": 'jacksonville-jaguars',
        "TEN": 'tennessee-titans',
        "KC": 'kansas-city-chiefs',
        "TB": 'tampa-bay-buccaneers',
        "LAR": 'los-angeles-rams',
        "PHI": 'philadelphia-eagles',
        "SEA": 'seattle-seahawks'
    }

    def __init__(self, output_dir: str = "data/raw/contracts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
             'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })