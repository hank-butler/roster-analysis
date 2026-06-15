import pytest
import pandas as pd
import plotly.graph_objects as go
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.nfc_west_comparison import DivisionAnalyzer


def _make_player(position, cap_hit, age, name="P", team="SF"):
    return PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )


@pytest.fixture
def two_team_data():
    return {
        "SF": [
            _make_player("QB", 30_000_000, 27, "Purdy", "SF"),
            _make_player("WR", 20_000_000, 25, "Aiyuk", "SF"),
            _make_player("OT", 15_000_000, 35, "Williams", "SF"),
        ],
        "SEA": [
            _make_player("QB", 25_000_000, 33, "Geno", "SEA"),
            _make_player("WR", 18_000_000, 27, "Metcalf", "SEA"),
        ],
    }


@pytest.fixture
def analyzer(two_team_data):
    return DivisionAnalyzer(two_team_data)


def test_constructor_values_all_rosters(two_team_data):
    da = DivisionAnalyzer(two_team_data)
    for team, roster in da._valued_rosters.items():
        assert all(p.expected_value != 0.0 for p in roster)


def test_compare_portfolio_metrics_returns_dataframe(analyzer):
    df = analyzer.compare_portfolio_metrics()
    assert isinstance(df, pd.DataFrame)


def test_compare_portfolio_metrics_columns(analyzer):
    df = analyzer.compare_portfolio_metrics()
    required = {"team", "total_value", "total_cost", "efficiency",
                "risk", "sharpe_ratio", "avg_age", "num_overvalued"}
    assert required.issubset(set(df.columns))


def test_compare_portfolio_metrics_one_row_per_team(analyzer, two_team_data):
    df = analyzer.compare_portfolio_metrics()
    assert len(df) == len(two_team_data)


def test_compare_position_allocation_returns_dataframe(analyzer):
    df = analyzer.compare_position_allocation()
    assert isinstance(df, pd.DataFrame)


def test_compare_position_allocation_has_position_columns(analyzer):
    df = analyzer.compare_position_allocation()
    from src.sb_template import POSITION_GROUPS
    for group in POSITION_GROUPS:
        assert group in df.columns


def test_rank_teams_default_metric(analyzer):
    df = analyzer.rank_teams()
    assert "rank" in df.columns
    assert "efficiency" in df.columns
    assert set(df["rank"].tolist()) == set(range(1, len(df) + 1))


def test_rank_teams_valid_metrics(analyzer):
    for metric in ("efficiency", "risk", "sharpe_ratio", "sb_similarity"):
        df = analyzer.rank_teams(metric=metric)
        assert "rank" in df.columns


def test_rank_teams_risk_ascending(analyzer):
    df = analyzer.rank_teams(metric="risk").sort_values("rank")
    assert df.iloc[0]["risk"] <= df.iloc[-1]["risk"]


def test_identify_division_advantages_keys(analyzer):
    result = analyzer.identify_division_advantages(primary_team="SF")
    assert set(result.keys()) == {"strengths", "weaknesses", "opportunities"}


def test_identify_division_advantages_lists_of_strings(analyzer):
    result = analyzer.identify_division_advantages(primary_team="SF")
    for key in ("strengths", "weaknesses", "opportunities"):
        assert isinstance(result[key], list)
        assert all(isinstance(s, str) for s in result[key])


def test_generate_division_report_keys(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    assert set(report.keys()) == {
        "metrics_df", "allocation_df", "rankings",
        "advantages", "sb_similarity", "figures",
    }


def test_generate_division_report_figures_are_plotly(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    for name, fig in report["figures"].items():
        assert isinstance(fig, go.Figure), f"Figure '{name}' is not a go.Figure"


def test_generate_division_report_figure_keys(analyzer):
    report = analyzer.generate_division_report(primary_team="SF")
    expected_keys = {
        "efficiency_scatter", "position_allocation",
        "age_distribution", "sb_radar", "player_value_scatter",
    }
    assert set(report["figures"].keys()) == expected_keys
