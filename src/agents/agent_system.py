import logging
from typing import Dict, List, Optional

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)


class AgentSystem:
    """Entry point for the NFL multi-agent analytics system.

    This is a stub. Full implementation is in Task 5 of the implementation plan.
    """

    def __init__(
        self,
        players: Optional[List[PlayerAsset]] = None,
        api_key: Optional[str] = None,
    ) -> None:
        raise NotImplementedError(
            "AgentSystem is not yet implemented. "
            "See docs/superpowers/plans/2026-06-15-ai-agent-layer.md Task 5."
        )

    def ask(self, query: str) -> Dict[str, object]:
        raise NotImplementedError("AgentSystem.ask() not yet implemented.")
