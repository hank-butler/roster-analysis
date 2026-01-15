from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class PlayerAsset:
    """
    Representing a player as a financial asset for roster optimization.

    """

    player_id: str
    name: str
    position: str
    team: str
    age: int

    # Contract Details
    cap_hit_2026: float
    years_remaining: int
    guaranteed_money: float
    total_contract_value: float

    # Performance metrics
    epa_total: float # Total EPA from past 3 seasons, considering adding a weight decay
    snaps_played: int
    games_missed: int

    # Calculated attributes
    expected_value: float = 0.0
    risk_score: float = 0.0
    fair_value: float = 0.0
    efficiency_ratio: float = 0.0
    sharpe_ratio: float = 0.0

class PlayerValuationModel:
    """
    Pricing theory based on bond pricing and portfolio theory
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        Risk free rate assumption of 0.03 set as default value, can be overwritten when creating new instance
        """

        self.position_baselines = {
            "QB": 35_000_000,
            "WR": 18_000_000,
            "RB": 8_000_000,
            "TE": 10_000_000,
            "OT": 18_000_000,
            "OG": 12_000_000,
            "C": 12_000_000,
            "EDGE": 20_000_000,
            "DL": 15_000_000,
            "LB": 12_000_000,
            "CB": 16_000_000,
            "S": 12_000_000,
            "K": 3_000_000,
            "P": 2_000_000,
            "LS": 1_500_000
        }

        self.epa_to_dollars = {
            "QB": 2_500_000,
            "WR": 1_800_000,
            "RB": 1_200_000,
            "TE": 1_500_000,
            "OT": 1_000_000,
            "OG": 900_000,
            "C": 900_000,
            "EDGE": 1_600_000,
            "DL": 1_400_000,
            "LB": 1_300_000,
            "CB": 1_600_000,
            "S": 1_400_000,
            "K": 500_000,
            "P": 400_000,
            "LS": 300_000
        }

        self.peak_ages = {
            "QB": 28,
            "WR": 26,
            "RB": 25,
            "TE": 27,
            "OT": 28,
            "OG": 28,
            "C": 29,
            "EDGE": 27,
            "DL": 27,
            "LB": 27,
            "CB": 27,
            "S": 27,
            "K": 30,
            "P": 30,
            "LS": 30
        }

    