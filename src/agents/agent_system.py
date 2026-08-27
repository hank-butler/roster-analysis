import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
import pandas as pd

from src.agents.contract_agent import ContractAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.scouting_agent import ScoutingAgent
from src.agents.strategy_agent import StrategyAgent
from src.player_valuation import PlayerAsset, PlayerValuationModel

logger = logging.getLogger(__name__)

_CSV_PATH = str(Path(__file__).parent.parent.parent / "data" / "processed" / "player_assets_ready.csv")


def _load_players_from_csv(path: str) -> List[PlayerAsset]:
    """Load and value players from the processed CSV.

    Args:
        path: Path to player_assets_ready.csv.

    Returns:
        List of valued PlayerAsset objects.

    Raises:
        FileNotFoundError: If the CSV does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Run: python collect_all_data.py"
        )
    df = pd.read_csv(p)
    players = []
    for _, row in df.iterrows():
        try:
            players.append(PlayerAsset(
                player_id=str(row["player_id"]),
                name=str(row["name"]),
                position=str(row["position"]),
                team=str(row["team"]),
                age=int(row["age"]),
                cap_hit_2026=float(row["cap_hit_2026"]),
                years_remaining=int(row["years_remaining"]),
                guaranteed_money=float(row["guaranteed_money"]),
                total_contract_value=float(row["total_contract_value"]),
                epa_total=float(row["epa_total"]),
                snaps_played=int(row["snaps_played"]),
                games_missed=int(row["games_missed"]),
            ))
        except Exception as exc:
            logger.warning("Skipping row for %s: %s", row.get("name", "?"), exc)

    model = PlayerValuationModel()
    valued = model.value_roster(players)
    logger.info("Loaded and valued %d players from %s", len(valued), path)
    return valued


class AgentSystem:
    """Top-level entry point for the multi-agent NFL analytics system.

    Creates one shared Anthropic client, routes queries via CoordinatorAgent,
    and dispatches to the appropriate specialist (Contract, Scouting, Strategy).
    Stateless — no conversation history between calls.
    """

    def __init__(
        self,
        players: Optional[List[PlayerAsset]] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialise the agent system.

        Args:
            players: Pre-loaded, pre-valued PlayerAsset list. If None, loads
                from data/processed/player_assets_ready.csv automatically.
            api_key: Anthropic API key. If None, reads ANTHROPIC_API_KEY env var.

        Raises:
            ValueError: If no API key is found.
            FileNotFoundError: If players=None and the CSV does not exist.
        """
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key= to AgentSystem()."
            )

        self._players = (
            players if players is not None
            else _load_players_from_csv(_CSV_PATH)
        )

        if not self._players:
            logger.warning(
                "AgentSystem initialised with 0 players — "
                "agent responses will lack grounding data"
            )

        client = anthropic.Anthropic(api_key=resolved_key)
        self._coordinator = CoordinatorAgent(client=client)
        self._agents = {
            "contract": ContractAgent(client=client),
            "scouting":  ScoutingAgent(client=client),
            "strategy":  StrategyAgent(client=client),
        }

    def ask(self, query: str) -> Dict[str, object]:
        """Answer a natural language NFL roster question.

        Routes to the most appropriate specialist agent and returns a
        structured response grounded in real player data.

        Args:
            query: Natural language question about the NFL roster.

        Returns:
            Dict with keys:
                query (str): the original question
                agent (str): which specialist answered, or 'error'
                response (str): Claude's natural language answer
                data_used (List[str]): player/team names injected as context
        """
        try:
            category = self._coordinator.route(query)
            agent = self._agents[category]
            return agent.run(query, self._players)
        except anthropic.APIError as exc:
            logger.warning("API error in AgentSystem.ask: %s", exc)
            return {
                "query": query,
                "agent": "error",
                "response": f"Agent encountered an error: {exc}",
                "data_used": [],
            }


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    system = AgentSystem()  # loads from CSV, reads ANTHROPIC_API_KEY

    sample_queries = [
        "Who are the most undervalued players on the Broncos?",
        "Generate a scouting report on Patrick Surtain II",
        "How does our cap allocation compare to Super Bowl winners?",
    ]

    for query in sample_queries:
        logger.info("\n" + "=" * 60)
        logger.info("Query: %s", query)
        result = system.ask(query)
        logger.info("Agent: %s", result["agent"])
        logger.info("Data used: %s", result["data_used"][:5])
        logger.info("Response:\n%s", result["response"])
