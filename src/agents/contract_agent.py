import logging
from typing import Dict, List

import anthropic

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_PLAYERS = 30

_SYSTEM_PROMPT = """You are an NFL cap analyst for the San Francisco 49ers.
You use a bond-pricing valuation model to assess player contracts.
Key metrics provided:
- Cap Hit: annual salary cap charge
- Fair Value: what the player's performance justifies
- Efficiency: expected value / cap hit (>1.0 = good value)
- Sharpe: risk-adjusted return (higher = better)
- Status: Overvalued / Undervalued / Fair

Answer the user's question using ONLY the data provided below.
Cite specific numbers. Never invent contract figures not in the data.
Write for a front office audience — professional, concise, actionable."""


def _overvalued_flag(player: PlayerAsset) -> str:
    if player.cap_hit_2026 > player.fair_value * 1.15 and player.fair_value > 0:
        return "Overvalued"
    if player.fair_value > player.cap_hit_2026 * 1.15:
        return "Undervalued"
    return "Fair"


def _format_player_row(p: PlayerAsset) -> str:
    return (
        f"{p.name} | {p.position} | "
        f"${p.cap_hit_2026:,.0f} | "
        f"${p.fair_value:,.0f} | "
        f"{p.efficiency_ratio:.2f} | "
        f"{p.sharpe_ratio:.2f} | "
        f"{_overvalued_flag(p)}"
    )


class ContractAgent:
    """Answers cap and contract analysis questions grounded in valuation model data."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a contract analysis query grounded in player data.

        Prioritises SF players, caps context at 30 players.

        Args:
            query: Natural language contract question.
            players: Pre-valued list of PlayerAsset objects.

        Returns:
            Dict with keys: query, agent, response, data_used.
        """
        sf = [p for p in players if p.team == "SF"]
        others = [p for p in players if p.team != "SF"]
        selected = (sf + others)[:_MAX_PLAYERS]

        header = "Name | Position | Cap Hit | Fair Value | Efficiency | Sharpe | Status"
        rows = [_format_player_row(p) for p in selected]
        data_block = "\n".join([header] + rows)

        logger.debug("ContractAgent injecting %d players into context", len(selected))

        full_prompt = f"PLAYER CONTRACT DATA:\n{data_block}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "contract",
            "response": response.content[0].text if response.content else "",
            "data_used": [p.name for p in selected],
        }
