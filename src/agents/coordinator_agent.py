import logging
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

_ROUTING_SYSTEM_PROMPT = """You are a routing classifier for an NFL analytics system.
Classify the user query into exactly one category:
- contract: cap space, salary, valuations, overvalued/undervalued players
- scouting: player reports, stats, performance, injuries, age
- strategy: roster construction, free agency, draft, division comparison, SB template
Reply with only one word: contract, scouting, or strategy."""

_MODEL = "claude-sonnet-4-6"


class CoordinatorAgent:
    """Routes natural language NFL queries to the appropriate specialist agent.

    Makes a single lightweight Claude API call that returns one classification word.
    Falls back to 'scouting' on any unexpected response.
    """

    CATEGORIES = ("contract", "scouting", "strategy")
    DEFAULT_FALLBACK = "scouting"

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def route(self, query: str) -> str:
        """Classify a query into one specialist category.

        Args:
            query: Natural language NFL question from the user.

        Returns:
            One of 'contract', 'scouting', or 'strategy'.
        """
        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=10,
            system=_ROUTING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
        )
        category = response.content[0].text.strip().lower()
        if category not in self.CATEGORIES:
            logger.warning(
                "Coordinator returned unexpected category '%s' — falling back to '%s'",
                category,
                self.DEFAULT_FALLBACK,
            )
            return self.DEFAULT_FALLBACK
        return category
