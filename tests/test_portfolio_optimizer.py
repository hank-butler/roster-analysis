import pytest
import pandas as pd
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.evolution_engine import RosterConstraints
from src.portfolio_optimizer import PortfolioOptimizer


def _make_player(position, cap_hit, age, name="Test", team="SF",
                 epa=5.0, expected_value=0.0, risk_score=0.2):
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=epa, snaps_played=800, games_missed=1,
    )
    p.expected_value = expected_value
    p.risk_score = risk_score
    p.fair_value = expected_value * (1 - risk_score)
    p.efficiency_ratio = expected_value / cap_hit if cap_hit > 0 else 0.0
    return p


@pytest.fixture
def small_roster():
    model = PlayerValuationModel()
    players = [
        PlayerAsset("sf_qb_p", "Purdy", "QB", "SF", 27,
                    23_000_000, 4, 10_000_000, 90_000_000, 45.0, 1050, 0),
        PlayerAsset("sf_wr_a", "Aiyuk", "WR", "SF", 26,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
    ]
    return model.value_roster(players)


@pytest.fixture
def simple_constraints():
    c = RosterConstraints()
    c.min_roster_size = 2
    c.max_roster_size = 4
    c.salary_cap = 200_000_000
    c.position_limits = {"QB": (1, 2), "WR": (1, 2)}
    return c


def test_constructor_defaults(small_roster):
    opt = PortfolioOptimizer(current_roster=small_roster)
    assert opt._available_players == []


def test_constructor_none_available_treated_as_empty(small_roster):
    opt = PortfolioOptimizer(current_roster=small_roster, available_players=None)
    assert opt._available_players == []


def test_constructor_values_players():
    raw = [
        PlayerAsset("sf_qb_x", "Raw", "QB", "SF", 27,
                    20_000_000, 3, 10_000_000, 60_000_000, 30.0, 900, 0),
    ]
    assert raw[0].expected_value == 0.0
    opt = PortfolioOptimizer(current_roster=raw)
    assert opt._current_roster[0].expected_value != 0.0


def test_pareto_optimal_excludes_dominated_player():
    model = PlayerValuationModel()
    players = [
        PlayerAsset("p_a", "A", "QB", "SF", 25, 10_000_000, 2, 5_000_000, 20_000_000, 50.0, 1000, 0),
        PlayerAsset("p_b", "B", "QB", "SF", 25, 20_000_000, 2, 10_000_000, 40_000_000, 20.0, 800, 0),
        PlayerAsset("p_c", "C", "QB", "SF", 25, 25_000_000, 2, 12_000_000, 50_000_000, 80.0, 1050, 0),
    ]
    valued = model.value_roster(players)
    opt = PortfolioOptimizer(current_roster=valued)
    pareto = opt.identify_pareto_optimal_players(valued)
    pareto_names = {p.name for p in pareto}
    assert "B" not in pareto_names
    assert "A" in pareto_names
    assert "C" in pareto_names


def test_pareto_optimal_single_player_always_optimal():
    model = PlayerValuationModel()
    players = [
        PlayerAsset("p_a", "OnlyOne", "QB", "SF", 25,
                    10_000_000, 2, 5_000_000, 20_000_000, 50.0, 1000, 0),
    ]
    valued = model.value_roster(players)
    opt = PortfolioOptimizer(current_roster=valued)
    pareto = opt.identify_pareto_optimal_players(valued)
    assert len(pareto) == 1


def test_marginal_value_returns_float(small_roster, simple_constraints):
    opt = PortfolioOptimizer(current_roster=small_roster, constraints=simple_constraints)
    model = PlayerValuationModel()
    candidate = model.value_roster([
        PlayerAsset("sf_qb_new", "New QB", "QB", "SF", 24,
                    15_000_000, 3, 7_000_000, 45_000_000, 60.0, 1050, 0)
    ])[0]
    result = opt.calculate_marginal_value(small_roster, candidate)
    assert isinstance(result, float)


def test_marginal_value_zero_when_no_position_match(small_roster, simple_constraints):
    opt = PortfolioOptimizer(current_roster=small_roster, constraints=simple_constraints)
    model = PlayerValuationModel()
    te_candidate = model.value_roster([
        PlayerAsset("sf_te_x", "TE Guy", "TE", "SF", 28,
                    10_000_000, 2, 5_000_000, 20_000_000, 15.0, 700, 1)
    ])[0]
    result = opt.calculate_marginal_value(small_roster, te_candidate)
    assert result == 0.0


def test_efficient_frontier_returns_dataframe(small_roster, simple_constraints):
    opt = PortfolioOptimizer(current_roster=small_roster, constraints=simple_constraints)
    df = opt.calculate_efficient_frontier(n_points=5)
    assert isinstance(df, pd.DataFrame)
    assert set(["risk", "efficiency", "return_value", "cap_utilization"]).issubset(set(df.columns))


def test_efficient_frontier_n_points_respected(small_roster, simple_constraints):
    opt = PortfolioOptimizer(current_roster=small_roster, constraints=simple_constraints)
    df = opt.calculate_efficient_frontier(n_points=3)
    assert len(df) <= 3


def test_position_efficient_allocation_keys(small_roster, simple_constraints):
    opt = PortfolioOptimizer(current_roster=small_roster, constraints=simple_constraints)
    result = opt.calculate_position_efficient_allocation()
    assert isinstance(result, dict)
    for group_data in result.values():
        assert set(group_data.keys()) == {"current_pct", "optimal_pct", "delta", "recommendation"}
        assert group_data["recommendation"] in ("increase", "decrease", "maintain")
