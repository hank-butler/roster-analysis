import logging
from typing import Dict, List

import anthropic

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_PLAYERS = 30

_SYSTEM_PROMPT = """You are a senior NFL scout for the San Francisco 49ers.
You write scouting reports and player assessments for coaches and general managers.
Write in plain English — translate stats into insights, not just numbers.
Guidelines:
- EPA (Expected Points Added): >15 = elite, 5-15 = above average, <5 = below average
- Games missed: 0-2 = durable, 3-6 = some concern, 7+ = significant injury risk
- Snaps played: indicates how central the player is to the scheme
Answer using ONLY the data provided below. Never invent stats not in the data."""


def _format_player_row(p: PlayerAsset) -> str:
    return (
        f"{p.name} | {p.position} | Age {p.age} | "
        f"EPA {p.epa_total:.1f} | "
        f"Snaps {p.snaps_played} | "
        f"Games missed {p.games_missed}"
    )


class ScoutingAgent:
    """Answers player scouting and performance questions grounded in stats data."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def _select_players(
        self, query: str, players: List[PlayerAsset]
    ) -> List[PlayerAsset]:
        """Select up to 30 players, prioritising name matches in the query.

        Args:
            query: The user's query string.
            players: Full player list.

        Returns:
            Up to 30 PlayerAsset objects, name-matched players first.
        """
        query_lower = query.lower()
        matched = [p for p in players if p.name.lower() in query_lower]
        others = [p for p in players if p.name.lower() not in query_lower]
        sf_matched = [p for p in matched if p.team == "SF"]
        other_matched = [p for p in matched if p.team != "SF"]
        sf_others = [p for p in others if p.team == "SF"]
        rest = [p for p in others if p.team != "SF"]
        ordered = sf_matched + other_matched + sf_others + rest
        return ordered[:_MAX_PLAYERS]

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a scouting query grounded in player performance data.

        Args:
            query: Natural language scouting question.
            players: Pre-valued list of PlayerAsset objects.

        Returns:
            Dict with keys: query, agent, response, data_used.
        """
        selected = self._select_players(query, players)

        header = "Name | Position | Age | EPA Total | Snaps Played | Games Missed"
        rows = [_format_player_row(p) for p in selected]
        data_block = "\n".join([header] + rows)

        logger.debug("ScoutingAgent injecting %d players into context", len(selected))

        full_prompt = f"PLAYER SCOUTING DATA:\n{data_block}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "scouting",
            "response": response.content[0].text,
            "data_used": [p.name for p in selected],
        }
