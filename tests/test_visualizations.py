import inspect
import pytest
import plotly.graph_objects as go
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.sb_template import SuperBowlTemplateAnalyzer
from src.visualizations import (
    plot_roster_efficiency_scatter,
    plot_position_allocation_comparison,
    plot_evolution_history,
    plot_player_value_scatter,
    plot_sb_similarity_radar,
    plot_age_distribution,
    TEAM_COLORS,
)


def _make_valued_player(position, cap_hit, age, name="P", team="DEN"):
    model = PlayerValuationModel()
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower()}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )
    return model.value_roster([p])[0]


@pytest.fixture
def den_roster():
    return [
        _make_valued_player("QB", 30_000_000, 27, "Nix", "DEN"),
        _make_valued_player("WR", 20_000_000, 25, "Sutton", "DEN"),
        _make_valued_player("OT", 15_000_000, 35, "Bolles", "DEN"),
    ]


@pytest.fixture
def teams_data(den_roster):
    kc = [_make_valued_player("QB", 25_000_000, 28, "Mahomes", "KC")]
    return {"DEN": den_roster, "KC": kc}


@pytest.fixture
def sb_template():
    return SuperBowlTemplateAnalyzer().build_sb_template()


def test_plot_roster_efficiency_scatter_returns_figure(teams_data):
    fig = plot_roster_efficiency_scatter(teams_data)
    assert isinstance(fig, go.Figure)


def test_plot_position_allocation_comparison_returns_figure(teams_data, sb_template):
    fig = plot_position_allocation_comparison(teams_data, sb_template)
    assert isinstance(fig, go.Figure)


def test_plot_evolution_history_returns_figure():
    history = [
        {"generation": 0, "best_fitness": 0.5, "avg_fitness": 0.3},
        {"generation": 1, "best_fitness": 0.7, "avg_fitness": 0.4},
        {"generation": 2, "best_fitness": 0.7, "avg_fitness": 0.5},
    ]
    fig = plot_evolution_history(history)
    assert isinstance(fig, go.Figure)


def test_plot_player_value_scatter_returns_figure(den_roster):
    fig = plot_player_value_scatter(den_roster, highlight_team="DEN")
    assert isinstance(fig, go.Figure)


def test_plot_sb_similarity_radar_returns_figure(teams_data, sb_template):
    fig = plot_sb_similarity_radar(teams_data, sb_template)
    assert isinstance(fig, go.Figure)


def test_plot_age_distribution_returns_figure(den_roster):
    fig = plot_age_distribution(den_roster)
    assert isinstance(fig, go.Figure)


def test_plot_evolution_history_empty_returns_figure():
    fig = plot_evolution_history([])
    assert isinstance(fig, go.Figure)


def test_plot_roster_efficiency_scatter_empty_dict():
    fig = plot_roster_efficiency_scatter({})
    assert isinstance(fig, go.Figure)


def test_afc_west_retarget_values(teams_data):
    # Assert TEAM_COLORS has expected AFC West values
    assert TEAM_COLORS == {"DEN": "#FB4F14", "KC": "#E31837", "LAC": "#0080C6", "LV": "#000000"}

    # Assert plot_roster_efficiency_scatter has correct title with em dash
    fig = plot_roster_efficiency_scatter(teams_data)
    assert fig.layout.title.text == "AFC West — Portfolio Risk vs Efficiency"

    # Assert plot_player_value_scatter default highlight_team is "DEN"
    sig = inspect.signature(plot_player_value_scatter)
    assert sig.parameters["highlight_team"].default == "DEN"
