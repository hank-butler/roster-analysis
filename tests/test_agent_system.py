import pytest
from unittest.mock import MagicMock
import anthropic

from src.agents.coordinator_agent import CoordinatorAgent
from src.player_valuation import PlayerAsset, PlayerValuationModel


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


# ---- ContractAgent --------------------------------------------------------

from src.agents.contract_agent import ContractAgent


def _make_valued_player(
    name: str, position: str, cap_hit: float, age: int, team: str = "SF"
) -> PlayerAsset:
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 3,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )
    return PlayerValuationModel().value_roster([p])[0]


@pytest.fixture
def sf_players():
    return [
        _make_valued_player("Brock Purdy", "QB", 23_700_000, 27),
        _make_valued_player("Nick Bosa", "DL", 22_990_000, 29),
        _make_valued_player("George Kittle", "TE", 14_100_000, 31),
    ]


def test_contract_agent_returns_required_keys(sf_players):
    agent = ContractAgent(client=_mock_client("Brock Purdy is overvalued."))
    result = agent.run("Who is overvalued?", sf_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_contract_agent_sets_agent_name(sf_players):
    agent = ContractAgent(client=_mock_client("Analysis here."))
    result = agent.run("any query", sf_players)
    assert result["agent"] == "contract"


def test_contract_agent_data_used_is_list_of_strings(sf_players):
    agent = ContractAgent(client=_mock_client("Response text."))
    result = agent.run("cap analysis", sf_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_contract_agent_data_used_contains_player_names(sf_players):
    agent = ContractAgent(client=_mock_client("Response."))
    result = agent.run("any", sf_players)
    assert "Brock Purdy" in result["data_used"]


def test_contract_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_contract_agent_query_echoed_in_result(sf_players):
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("Who is the most overvalued?", sf_players)
    assert result["query"] == "Who is the most overvalued?"


# ---- ScoutingAgent --------------------------------------------------------

from src.agents.scouting_agent import ScoutingAgent


def test_scouting_agent_returns_required_keys(sf_players):
    agent = ScoutingAgent(client=_mock_client("Kittle is elite."))
    result = agent.run("Scouting report on George Kittle", sf_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_scouting_agent_sets_agent_name(sf_players):
    agent = ScoutingAgent(client=_mock_client("Report."))
    result = agent.run("any", sf_players)
    assert result["agent"] == "scouting"


def test_scouting_agent_data_used_is_list_of_strings(sf_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", sf_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_scouting_agent_prioritises_name_match(sf_players):
    """When query mentions a player name, that player should appear in data_used."""
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Tell me about George Kittle", sf_players)
    assert "George Kittle" in result["data_used"]


def test_scouting_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_scouting_agent_query_echoed(sf_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Is Bosa injury-prone?", sf_players)
    assert result["query"] == "Is Bosa injury-prone?"
