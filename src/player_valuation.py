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

