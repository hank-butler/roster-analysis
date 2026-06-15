import logging
from typing import Dict, List

import pandas as pd

from src.player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer
from src.sb_template import POSITION_GROUPS, SuperBowlTemplateAnalyzer
from src.visualizations import (
    plot_age_distribution,
    plot_player_value_scatter,
    plot_position_allocation_comparison,
    plot_roster_efficiency_scatter,
    plot_sb_similarity_radar,
)

logger = logging.getLogger(__name__)

_VALID_METRICS = ("efficiency", "risk", "sharpe_ratio", "sb_similarity")


class DivisionAnalyzer:
    """Coordination layer for NFC West division analysis.

    Values all roster inputs at init so downstream methods receive
    pre-valued PlayerAsset objects.
    """

    def __init__(self, teams_data: Dict[str, List[PlayerAsset]]) -> None:
        """Initialise and value all team rosters.

        Args:
            teams_data: Dict mapping team abbreviation (e.g. 'SF') to roster.
        """
        model = PlayerValuationModel()
        self._valued_rosters: Dict[str, List[PlayerAsset]] = {
            team: model.value_roster(list(roster))
            for team, roster in teams_data.items()
        }
        self._sb_analyzer = SuperBowlTemplateAnalyzer()
        self._sb_template = self._sb_analyzer.build_sb_template()

    def compare_portfolio_metrics(self) -> pd.DataFrame:
        """Return one row per team with portfolio-level metrics.

        Returns:
            DataFrame with columns: team, total_value, total_cost, efficiency,
            risk, sharpe_ratio, avg_age, num_overvalued.
        """
        rows = []
        for team, roster in self._valued_rosters.items():
            if not roster:
                continue
            pa = PortfolioAnalyzer(roster)
            summary = pa.summary_report()
            rows.append({
                "team": team,
                "total_value": round(summary["total_value"], 0),
                "total_cost": round(summary["total_cost"], 0),
                "efficiency": round(summary["efficiency"], 4),
                "risk": round(summary["risk"], 4),
                "sharpe_ratio": round(summary["sharpe_ratio"], 4),
                "avg_age": round(summary["avg_roster_age"], 1),
                "num_overvalued": summary["num_overvalued"],
            })
        return pd.DataFrame(rows)

    def compare_position_allocation(self) -> pd.DataFrame:
        """Return cap % per position group for each team.

        Returns:
            DataFrame with team as index and position groups as columns.
        """
        rows = []
        groups = list(POSITION_GROUPS.keys())
        for team, roster in self._valued_rosters.items():
            alloc = self._sb_analyzer.calculate_position_allocation(roster)
            row = {"team": team}
            row.update({g: round(alloc.get(g, 0.0), 2) for g in groups})
            rows.append(row)
        return pd.DataFrame(rows).set_index("team")

    def rank_teams(self, metric: str = "efficiency") -> pd.DataFrame:
        """Rank all teams by a given metric.

        Args:
            metric: One of 'efficiency', 'risk', 'sharpe_ratio', 'sb_similarity'.
                For 'risk', lower is better (ranks ascending).
                All others rank descending.

        Returns:
            DataFrame with columns: team, <metric>, rank.
        """
        if metric not in _VALID_METRICS:
            raise ValueError(f"metric must be one of {_VALID_METRICS}, got '{metric}'")

        if metric == "sb_similarity":
            scores = {
                team: self._sb_analyzer.calculate_similarity_score(roster)[
                    "overall_similarity"
                ]
                for team, roster in self._valued_rosters.items()
            }
            df = pd.DataFrame([
                {"team": team, "sb_similarity": score}
                for team, score in scores.items()
            ])
            df = df.sort_values("sb_similarity", ascending=False).reset_index(drop=True)
        else:
            metrics_df = self.compare_portfolio_metrics()
            df = metrics_df[["team", metric]].copy()
            ascending = metric == "risk"
            df = df.sort_values(metric, ascending=ascending).reset_index(drop=True)

        df["rank"] = range(1, len(df) + 1)
        return df

    def identify_division_advantages(
        self, primary_team: str = "SF"
    ) -> Dict[str, List[str]]:
        """Compare primary team's position allocations to the division average.

        Args:
            primary_team: Team abbreviation for the primary team.

        Returns:
            Dict with keys: strengths, weaknesses, opportunities.
            strengths = groups where primary leads division avg.
            weaknesses = groups where primary trails.
            opportunities = weaknesses where primary is ranked 3rd or 4th.
        """
        alloc_df = self.compare_position_allocation()

        if primary_team not in alloc_df.index:
            logger.warning("Primary team '%s' not in teams_data", primary_team)
            return {"strengths": [], "weaknesses": [], "opportunities": []}

        groups = list(POSITION_GROUPS.keys())
        primary_alloc = alloc_df.loc[primary_team]
        division_avg = alloc_df[groups].mean()

        strengths, weaknesses, opportunities = [], [], []

        for group in groups:
            primary_pct = primary_alloc[group]
            avg_pct = division_avg[group]

            if primary_pct > avg_pct:
                strengths.append(group)
            elif primary_pct < avg_pct:
                weaknesses.append(group)
                group_series = alloc_df[group].sort_values(ascending=False)
                rank = list(group_series.index).index(primary_team) + 1
                if rank >= 3:
                    opportunities.append(group)

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
        }

    def generate_division_report(
        self, primary_team: str = "SF"
    ) -> Dict:
        """Generate a complete division analysis report with metrics and figures.

        Note: plot_evolution_history is excluded — it requires EvolutionEngine output.

        Args:
            primary_team: Team abbreviation for team-specific figures.

        Returns:
            Dict with keys: metrics_df, allocation_df, rankings, advantages,
            sb_similarity, figures.
        """
        metrics_df = self.compare_portfolio_metrics()
        allocation_df = self.compare_position_allocation()
        advantages = self.identify_division_advantages(primary_team)
        rankings = {m: self.rank_teams(m) for m in _VALID_METRICS}
        sb_similarity = {
            team: self._sb_analyzer.calculate_similarity_score(roster)
            for team, roster in self._valued_rosters.items()
        }
        primary_roster = self._valued_rosters.get(primary_team, [])
        figures = {
            "efficiency_scatter": plot_roster_efficiency_scatter(self._valued_rosters),
            "position_allocation": plot_position_allocation_comparison(
                self._valued_rosters, self._sb_template
            ),
            "age_distribution": plot_age_distribution(primary_roster),
            "sb_radar": plot_sb_similarity_radar(
                self._valued_rosters, self._sb_template
            ),
            "player_value_scatter": plot_player_value_scatter(
                primary_roster, highlight_team=primary_team
            ),
        }
        return {
            "metrics_df": metrics_df,
            "allocation_df": allocation_df,
            "rankings": rankings,
            "advantages": advantages,
            "sb_similarity": sb_similarity,
            "figures": figures,
        }


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    demo_teams = {
        "SF": [
            PlayerAsset("sf_qb", "Purdy", "QB", "SF", 27,
                        37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
            PlayerAsset("sf_wr", "Aiyuk", "WR", "SF", 26,
                        24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
            PlayerAsset("sf_ot", "Williams", "OT", "SF", 35,
                        23_000_000, 1, 5_000_000, 23_000_000, 0.0, 1050, 0),
        ],
        "SEA": [
            PlayerAsset("sea_qb", "Geno", "QB", "SEA", 33,
                        20_000_000, 1, 10_000_000, 20_000_000, 15.0, 900, 2),
            PlayerAsset("sea_wr", "Metcalf", "WR", "SEA", 27,
                        22_000_000, 3, 11_000_000, 66_000_000, 18.0, 950, 1),
        ],
    }

    da = DivisionAnalyzer(demo_teams)
    logger.info("Portfolio Metrics:\n%s", da.compare_portfolio_metrics().to_string())
    logger.info("Rankings (efficiency):\n%s", da.rank_teams("efficiency").to_string())
    adv = da.identify_division_advantages("SF")
    logger.info("SF Strengths: %s", adv["strengths"])
    logger.info("SF Weaknesses: %s", adv["weaknesses"])
    logger.info("SF Opportunities: %s", adv["opportunities"])
    report = da.generate_division_report("SF")
    logger.info("Report figure keys: %s", list(report["figures"].keys()))
