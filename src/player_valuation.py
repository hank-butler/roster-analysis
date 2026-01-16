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

    def calculate_expected_value(self, player: PlayerAsset) -> float:
        """
        Calculates expected performance value using assumptions established above

        =========
        ARGUMENTS:
        =========
        PlayerAsset: The player being valued

        =======
        RETURNS:
        =======
        float: The calculated expected value for the player

        ======
        RAISES:
        ======
        TypeError
        """

        base_value = self.position_baselines.get(player.position, 10_000_000)

        epa_value = player.epa_total * self.epa_to_dollars.get(player.position, 1_000_000)

        expected_plays = 1_000 # approximate number of plays in a 17-game season

        snap_factor = min(player.snaps_played / expected_plays, 1.5) # capping at 150%

        # calculating raw performance value
        performance_value = base_value + epa_value
        adjusted_value = performance_value * snap_factor

        return max(adjusted_value, 0) # ensures number won't be negative
    
def calculate_risk_score(self, player: PlayerAsset) -> float:
    """
    Quantifying risk based on age, injury history, and position.

    Simplifying assumptions made, can be adjusted.

    =========
    ARGUMENTS
    =========
    player: PlayerAsset, the player getting the risk calculation

    =======
    RETURNS
    =======
    float: player's risk score

    ======
    RAISES
    ======

    
    """
    risk_components = []

    injury_risk = min(player.games_missed / 51, 0.5) # 51 for 3 full regular seasons
    risk_components.append(injury_risk)

    peak_age = self.peak_ages.get(player.position, 27) # simplifying assumption of player peak at 27 years due to avg NFL career being ~5 seasons
    age_diff = player.age - peak_age

    if age_diff <= 0:
        age_risk = 0.0
    elif age_diff <= 2:
        age_risk = 0.1
    elif age_diff <= 4:
        age_risk = 0.3
    else:
        age_risk = 0.5

    risk_components.append(age_risk)

    position_risk = {
        "QB": 0.1,
        "WR": 0.2,
        "RB": 0.4,
        "TE": 0.2,
        "OT": 0.15,
        "OG": 0.15,
        "C": 0.15,
        "EDGE": 0.25,
        "DL": 0.25,
        "LB": 0.2,
        "CB": 0.2,
        "S": 0.2,
        "K": 0.1,
        "P": 0.1,
        "LS": 0.1
    }

    risk_components.append(position_risk)

    # combined risk scores 
    total_risk = (
        0.4*risk_components[0] +
        0.4*risk_components[1] +
        0.2*risk_components[2]
    )

    return total_risk