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
    assert coordinator.route("Generate a scouting report on Evan Engram") == "scouting"


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
    name: str, position: str, cap_hit: float, age: int, team: str = "DEN"
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
def den_players():
    return [
        _make_valued_player("Bo Nix", "QB", 23_700_000, 27),
        _make_valued_player("Nick Bosa", "DL", 22_990_000, 29),
        _make_valued_player("Evan Engram", "TE", 14_100_000, 31),
    ]


def test_contract_agent_returns_required_keys(den_players):
    agent = ContractAgent(client=_mock_client("Bo Nix is overvalued."))
    result = agent.run("Who is overvalued?", den_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_contract_agent_sets_agent_name(den_players):
    agent = ContractAgent(client=_mock_client("Analysis here."))
    result = agent.run("any query", den_players)
    assert result["agent"] == "contract"


def test_contract_agent_data_used_is_list_of_strings(den_players):
    agent = ContractAgent(client=_mock_client("Response text."))
    result = agent.run("cap analysis", den_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_contract_agent_data_used_contains_player_names(den_players):
    agent = ContractAgent(client=_mock_client("Response."))
    result = agent.run("any", den_players)
    assert "Bo Nix" in result["data_used"]


def test_contract_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_contract_agent_query_echoed_in_result(den_players):
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("Who is the most overvalued?", den_players)
    assert result["query"] == "Who is the most overvalued?"


# ---- ScoutingAgent --------------------------------------------------------

from src.agents.scouting_agent import ScoutingAgent


def test_scouting_agent_returns_required_keys(den_players):
    agent = ScoutingAgent(client=_mock_client("Engram is elite."))
    result = agent.run("Scouting report on Evan Engram", den_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_scouting_agent_sets_agent_name(den_players):
    agent = ScoutingAgent(client=_mock_client("Report."))
    result = agent.run("any", den_players)
    assert result["agent"] == "scouting"


def test_scouting_agent_data_used_is_list_of_strings(den_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", den_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_scouting_agent_prioritises_name_match(den_players):
    """When query mentions a player name, that player should appear in data_used."""
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Tell me about Evan Engram", den_players)
    assert "Evan Engram" in result["data_used"]


def test_scouting_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_scouting_agent_query_echoed(den_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Is Bosa injury-prone?", den_players)
    assert result["query"] == "Is Bosa injury-prone?"


from src.agents.strategy_agent import StrategyAgent


@pytest.fixture
def multi_team_players():
    """Players from multiple AFC West teams for StrategyAgent."""
    den = [_make_valued_player(f"DEN Player {i}", pos, 10_000_000, 27, "DEN")
           for i, pos in enumerate(["QB", "WR", "DL"])]
    kc = [_make_valued_player(f"KC Player {i}", pos, 8_000_000, 28, "KC")
          for i, pos in enumerate(["QB", "WR"])]
    return den + kc


def test_strategy_agent_returns_required_keys(multi_team_players):
    agent = StrategyAgent(client=_mock_client("Focus on pass rush."))
    result = agent.run("What should we prioritise in free agency?", multi_team_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_strategy_agent_sets_agent_name(multi_team_players):
    agent = StrategyAgent(client=_mock_client("Strategy response."))
    result = agent.run("any", multi_team_players)
    assert result["agent"] == "strategy"


def test_strategy_agent_data_used_contains_team_names(multi_team_players):
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("how do we compare?", multi_team_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(t, str) for t in result["data_used"])
    assert len(result["data_used"]) > 0


def test_strategy_agent_query_echoed(multi_team_players):
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("How do we compare to the SB template?", multi_team_players)
    assert result["query"] == "How do we compare to the SB template?"


def test_strategy_agent_handles_single_team_data():
    """Should not crash when only one team's data is available."""
    den_only = [_make_valued_player(f"P {i}", "QB", 10_000_000, 27, "DEN")
                for i in range(3)]
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("what should we do?", den_only)
    assert result["agent"] == "strategy"
    assert "response" in result


import os
from unittest.mock import MagicMock, patch

from src.agents.agent_system import AgentSystem


# ---- AgentSystem: constructor ---------------------------------------------

def test_agent_system_raises_if_no_api_key(den_players, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AgentSystem(players=den_players, api_key=None)


def _make_simple_client(response_text: str) -> MagicMock:
    """Return a simple mock client (no spec) safe to use inside patch blocks."""
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def test_agent_system_accepts_api_key_param(den_players):
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _make_simple_client("contract")
        system = AgentSystem(players=den_players, api_key="sk-test-key")
    assert system is not None


def test_agent_system_accepts_pre_loaded_players(den_players):
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _make_simple_client("contract")
        system = AgentSystem(players=den_players, api_key="sk-test")
    assert system._players is not None
    assert len(system._players) == len(den_players)


def test_agent_system_loads_from_csv_when_no_players(tmp_path, monkeypatch):
    """When players=None, AgentSystem loads from player_assets_ready.csv."""
    import pandas as pd

    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([{
        "player_id": "den_qb_test", "name": "Test QB", "position": "QB",
        "team": "DEN", "age": 27, "cap_hit_2026": 20_000_000,
        "years_remaining": 3, "guaranteed_money": 10_000_000,
        "total_contract_value": 60_000_000, "epa_total": 30.0,
        "snaps_played": 1000, "games_missed": 0,
    }]).to_csv(csv_path, index=False)

    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _make_simple_client("contract")
        with patch("src.agents.agent_system._CSV_PATH", str(csv_path)):
            system = AgentSystem(players=None, api_key="sk-test")

    assert len(system._players) == 1
    assert system._players[0].name == "Test QB"


# ---- AgentSystem: ask() ---------------------------------------------------

def _make_system_with_mock(players, route_response: str, agent_response: str):
    """Helper: AgentSystem with two sequential mocked API responses."""
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        text = route_response if call_count == 1 else agent_response
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        return msg

    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = side_effect

    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = client
        system = AgentSystem(players=players, api_key="sk-test")

    return system


def test_ask_returns_required_keys(den_players):
    system = _make_system_with_mock(den_players, "contract", "Nix is overvalued.")
    result = system.ask("Who is most overvalued?")
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_ask_routes_to_contract_agent(den_players):
    system = _make_system_with_mock(den_players, "contract", "Cap analysis here.")
    result = system.ask("Who is overvalued?")
    assert result["agent"] == "contract"


def test_ask_routes_to_scouting_agent(den_players):
    system = _make_system_with_mock(den_players, "scouting", "Engram is elite.")
    result = system.ask("Tell me about Engram")
    assert result["agent"] == "scouting"


def test_ask_routes_to_strategy_agent(den_players):
    system = _make_system_with_mock(den_players, "strategy", "Target pass rush.")
    result = system.ask("What positions should we target?")
    assert result["agent"] == "strategy"


def test_ask_returns_error_dict_on_api_error(den_players):
    """API error → returns error dict, does not raise."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = client
        system = AgentSystem(players=den_players, api_key="sk-test")

    result = system.ask("any question")
    assert result["agent"] == "error"
    assert "error" in result["response"].lower()
    assert result["data_used"] == []


def test_ask_echoes_query(den_players):
    system = _make_system_with_mock(den_players, "scouting", "response")
    result = system.ask("Is Bosa healthy?")
    assert result["query"] == "Is Bosa healthy?"
