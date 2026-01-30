import random
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass, field
from copy import deepcopy
import numpy as np
import pandas as pd
from tqdm import tqdm

from player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer

@dataclass
class RosterConstraints:
    """
    Setting up constraints for NFL active roster. Current active roster size is 53 players

    Base Salary Cap default value from https://overthecap.com/salary-cap-space
    """
    max_roster_size: int = 53
    min_roster_size: int = 53
    salary_cap: float = 295_500_000

    # Position requirements (min, max)
    position_limits: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        'QB': (2, 3),
        'RB': (3, 5),
        'WR': (5, 7),
        'TE': (2, 4),
        'OT': (4, 6),
        'OG': (4, 6),
        'C': (2, 3),
        'EDGE': (4, 6),
        'DL': (4, 6),
        'LB': (4, 6),
        'CB': (4, 6),
        'S': (3, 5),
        'K': (1, 1),
        'P': (1, 1),
        'LS': (1, 1)
    })

class Chromosome:
    """
    Using the evolution algorithm, need to represent the chromosomes and genes.

    A Chromosome represents one possible roster configuration.

    Genes = player selections
    """

    def __init__(self, players: List[PlayerAsset]):
        self.players = players
        self.fitness = None,
        self._analyzer = None

    def __len__(self):
        return len(self.players)
    
    @property
    def analyzer(self) -> PortfolioAnalyzer:
        """
        Load analzyer lazily
        """
        if self._analyzer is None:
            self._analyzer = PortfolioAnalyzer(self.players)
        return self._analyzer
    
    def total_cap(self) -> float:
        """
        Total Cap hit of roster as a float
        """
        return sum(p.cap_hit_2026 for p in self.players)
    
    def position_counts(self) -> Dict[str, int]:
        """
        Count players by position

        Returns a dictionary with player pos as key, count of players by position as int as value
        """
        counts = {}
        for player in self.players:
            counts[player.position] = counts.get(player.position, 0) + 1 # if position key doesn't exist yet, return 0
        return counts
    
    def is_valid(self, constraints: RosterConstraints) -> bool:
        """
        Method to ensure roster constraints are met

        Returns True if met, False otherwise
        """
        if len(self.players) < constraints.min_roster_size:
            return False
        if len(self.players) > constraints.max_roster_size:
            return False
        
        if self.total_cap() > constraints.salary_cap:
            return False
        
        # Check position requirements
        pos_counts = self.position_counts()
        for positition, (min_count, max_count) in constraints.position_limits.items():
            count = pos_counts.get(position, 0)
            if count < min_count or count > max_count:
                return False
        
        return True
