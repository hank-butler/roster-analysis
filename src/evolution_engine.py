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
    pass