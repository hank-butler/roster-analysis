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

        risk_components.append(position_risk.get(player.position, 0.2))

        # combined risk scores 
        total_risk = (
            0.4*risk_components[0] +
            0.4*risk_components[1] +
            0.2*risk_components[2]
        )

        return total_risk

    def calculate_npv(self, player: PlayerAsset) -> float:
        """
        Docstring for calculate_npv
        
        :param self: Description
        :param player: Description
        :type player: PlayerAsset
        :return: Description
        :rtype: float
        """

        risk_premium = player.risk_score *.10
        discount_rate = self.risk_free_rate + risk_premium

        annual_value = player.expected_value / max(player.years_remaining, 1)
        annual_cost = player.cap_hit_2026
        annual_net = annual_value-annual_cost

        npv = 0

        for year in range(player.years_remaining):
            npv += annual_net / ((1 + discount_rate) ** year)

        return npv

    def calculate_fair_value(self, player: PlayerAsset) -> float:
        """
        Docstring for calculate_fair_value
        
        :param self: Description
        :param player: Description
        :type player: PlayerAsset
        :return: Description
        :rtype: float
        """

        expected_value = player.expected_value
        risk_multiplier = 1 - player.risk_score

        fair_value = expected_value * risk_multiplier

        return fair_value
    
    def calculate_efficiency_ratio(self, player:PlayerAsset) -> float:
        """
        Docstring for calculate_efficiency_ratio
        
        :param self: Description
        :param player: Description
        :type player: PlayerAsset
        :return: Description
        :rtype: float
        
        Value per dollar (similar idea to bond yield)
        """
        if player.cap_hit_2026 <= 0:
            return 0.0
        
        return player.expected_value / player.cap_hit_2026
    
    def calculate_sharpe_ratio(self, player:PlayerAsset) -> float:
        """
        Risk-adjusted return
        (expected return - risk-free rate) / risk
        
        :param self: Description
        :param player: Description
        :type player: PlayerAsset
        :return: Description
        :rtype: float
        """

        if player.risk_score <= 0:
            return 0.0
        
        excess_return = (player.expected_value - player.cap_hit_2026)

        return excess_return / (player.risk_score * player.cap_hit_2026)
    
    def value_player(self, player: PlayerAsset) -> PlayerAsset:
        """
        Complete valuation of a player from previous methods
        """
        player.expected_value = self.calculate_expected_value(player)
        player.risk_score = self.calculate_risk_score(player)
        player.fair_value = self.calculate_fair_value(player)
        player.efficiency_ratio = self.calculate_efficiency_ratio(player)
        player.sharpe_ratio = self.calculate_sharpe_ratio(player)

        return player
    
    def value_roster(self, players: List[PlayerAsset]) -> List[PlayerAsset]:
        """
        Values an entire roster of inputs

        Output is a list of player assets
        """

        return [self.value_player(p) for p in players]
    

class PortfolioAnalyzer:
    """
    Analyzes entire roster as asset portfolio
    """

    def __init__(self, players: List[PlayerAsset]):
        self.players = players
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        """
        Convert players list to Pandas DataFrame
        """
        data = []

        for p in self.players:
            data.append({
                'name': p.name,
                'position': p.position,
                'age': p.age,
                'cap_hit': p.cap_hit_2026,
                'expected_value': p.expected_value,
                'fair_value': p.fair_value,
                'risk_score': p.risk_score,
                'efficiency_ratio': p.efficiency_ratio,
                'sharpe_ratio': p.sharpe_ratio,
                'npv': p.expected_value - p.cap_hit_2026
            })

        return pd.DataFrame(data)
    
    def total_value(self) -> float:
        """
        Total value of a roster
        """
        return self.df["expected_value"].sum()
    
    def total_cost(self) -> float:
        """
        Total salary cap hit for a roster
        """
        return self.df["cap_hit"].sum()

    def portfolio_efficiency(self) -> float:
        """
        Overall efficiency ratio
        """
        return self.total_value() / self.total_cost() if self.total_cost() > 0 else 0
    
    def portfolio_risk(self) -> float:
        """
        Weighted average risk
        """
        total_cap = self.total_cost()

        if total_cap == 0:
            return 0
        
        weighted_risk = sum(
            p.risk_score * (p.cap_hit_2026 / total_cap) for p in self.players
        )

        return weighted_risk
    
    def portfolio_sharpe(self) -> float:
        """
        Sharpe ratio for roster portfolio
        """
        excess_return = self.total_value() - self.total_cost()
        risk = self.portfolio_risk()

        if risk == 0:
            return 0
        
        return excess_return / (risk * self.total_cost())
    
    def position_allocation(self) -> Dict[str, float]:
        """
        % of cap allocated to each position

        
        """
        total_cap = self.total_cost()

        position_spending = self.df.groupby("position")['cap_hit'].sum()

        return (position_spending / total_cap * 100).to_dict()
    
    def identify_overvalued(self, threshold: float=1.15, desc=True) -> pd.DataFrame:
        """
        Find overvalued players (cap hit > fair value * threshold)

        Threshold defaulted to 1.15, but can be overwritten with specified value.
        """
        overvalued = self.df[self.df["cap_hit"] > self.df["fair_value"]*threshold].copy() # make a copy to not impact underlying df

        overvalued['overvalued_by'] = overvalued["cap_hit"] - overvalued["fair_value"]
        overvalued["pct_overvalued"] = (
            (overvalued["cap_hit"] / overvalued["fair_value"] - 1) * 100
        )

        return overvalued.sort_values(by="overvalued_by", ascending=not desc)
    
    def identify_undervalued(self, threshold: float=0.85, desc=True) -> pd.DataFrame:
        """
        Find undervalued players (cap hit < fair_value * threshold)

        Threshold defaulted to 0.85
        """

        undervalued = self.df[self.df['cap_hit'] < self.df['fair_value']*threshold].copy()

        undervalued['undervalued_by'] = undervalued['fair_value'] - undervalued['cap_hit'] 

        undervalued['pct_undervalued'] = (
            (1 - undervalued['cap_hit'] / undervalued['fair_value']) * 100
        )

        return undervalued.sort_values(by='undervalued_by', ascending=not desc)
    
    def summary_report(self) -> Dict:
        """
        Complete summary report of portfolio
        """
        return {
            "total_value": self.total_value(),
            "total_cost": self.total_cost(),
            "efficiency": self.portfolio_efficiency(),
            "risk": self.portfolio_risk(),
            "sharpe_ratio": self.portfolio_sharpe(),
            "position_allocation": self.position_allocation(),
            "num_overvalued": len(self.identify_overvalued()),
            "num_undervalued": len(self.identify_undervalued()),
            "avg_roster_age": self.df["age"].mean(),
            "total_players": len(self.players)
        }


if __name__ == "__main__":
    main()







