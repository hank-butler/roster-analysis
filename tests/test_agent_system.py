import pytest
from unittest.mock import MagicMock
import anthropic

from src.agents.coordinator_agent import CoordinatorAgent


# ---- Shared helpers -------------------------------------------------------

def _mock_client(response_text: str) -> MagicMock:
    """Return a mock anthropic.Anthropic that returns response_text."""
    client = MagicMock(spec=anthropic.Anthropic)
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def _error_client() -> MagicMock:
    """Return a mock client that raises APIConnectionError."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    return client


# ---- CoordinatorAgent -----------------------------------------------------

def test_coordinator_routes_contract_query():
    coordinator = CoordinatorAgent(client=_mock_client("contract"))
    assert coordinator.route("Who is our most overvalued player?") == "contract"


def test_coordinator_routes_scouting_query():
    coordinator = CoordinatorAgent(client=_mock_client("scouting"))
    assert coordinator.route("Generate a scouting report on George Kittle") == "scouting"


def test_coordinator_routes_strategy_query():
    coordinator = CoordinatorAgent(client=_mock_client("strategy"))
    assert coordinator.route("What positions should we target in free agency?") == "strategy"


def test_coordinator_fallback_on_unexpected_response():
    coordinator = CoordinatorAgent(client=_mock_client("unknown category"))
    result = coordinator.route("some ambiguous query")
    assert result == "scouting"  # DEFAULT_FALLBACK


def test_coordinator_fallback_on_empty_response():
    coordinator = CoordinatorAgent(client=_mock_client(""))
    result = coordinator.route("anything")
    assert result == "scouting"


def test_coordinator_strips_whitespace_from_response():
    coordinator = CoordinatorAgent(client=_mock_client("  contract  \n"))
    assert coordinator.route("cap space?") == "contract"
