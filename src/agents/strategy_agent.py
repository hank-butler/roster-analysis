import logging
from typing import Dict, List

import anthropic

from src.afc_west_comparison import DivisionAnalyzer
from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are a strategic roster advisor for the San Francisco 49ers.
You think in terms of cap allocation, portfolio efficiency, and competitive positioning.
Use the team comparison data below to inform specific, actionable recommendations.
Focus on: cap allocation gaps vs SB winners, division strengths and weaknesses,
and free agency / draft priorities.
Answer using ONLY the data provided. Be concise and front-office appropriate."""


class StrategyAgent:
    """Answers team strategy questions using DivisionAnalyzer team-level summaries."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def _build_context(self, players: List[PlayerAsset]) -> tuple:
        """Build team-level context string and list of teams present.

        Args:
            players: Pre-valued list of PlayerAsset objects across all teams.

        Returns:
            Tuple of (context_string, list_of_team_abbreviations).
        """
        teams_data: Dict[str, List[PlayerAsset]] = {}
        for p in players:
            teams_data.setdefault(p.team, []).append(p)

        team_list = sorted(teams_data.keys())

        if not teams_data:
            return "No team data available.", []

        try:
            analyzer = DivisionAnalyzer(teams_data)
            metrics_df = analyzer.compare_portfolio_metrics()
            alloc_df = analyzer.compare_position_allocation()

            metrics_text = metrics_df.to_string(index=False)
            alloc_text = alloc_df.to_string()

            sb_lines = []
            if "SF" in teams_data:
                sb_analyzer = SuperBowlTemplateAnalyzer()
                sim = sb_analyzer.calculate_similarity_score(teams_data["SF"])
                sb_lines.append(
                    f"SF SB Template Similarity: {sim['overall_similarity']:.1f}/100"
                )
                for gap in sim["gaps"]:
                    sb_lines.append(f"  Gap: {gap}")

            sections = [
                "TEAM PORTFOLIO METRICS:",
                metrics_text,
                "",
                "CAP ALLOCATION BY POSITION GROUP (% of cap):",
                alloc_text,
            ]
            if sb_lines:
                sections += ["", "SF vs SB TEMPLATE:"] + sb_lines

            context = "\n".join(sections)
        except Exception as exc:
            logger.warning("DivisionAnalyzer failed: %s — using minimal context", exc)
            context = f"Teams present: {', '.join(team_list)}"

        return context, team_list

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a strategy query using team-level portfolio summaries.

        Args:
            query: Natural language strategy question.
            players: Pre-valued list of PlayerAsset objects (may span multiple teams).

        Returns:
            Dict with keys: query, agent, response, data_used.
            Note: data_used contains team abbreviations, not player names.
        """
        context, teams = self._build_context(players)
        logger.debug("StrategyAgent building context for teams: %s", teams)

        full_prompt = f"{context}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "strategy",
            "response": response.content[0].text if response.content else "",
            "data_used": teams,
        }
