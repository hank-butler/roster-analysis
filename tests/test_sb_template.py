import pytest
from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer, POSITION_GROUPS


def _make_player(position, cap_hit, age, name="Test", team="SF", epa=5.0,
                 expected_value=0.0, risk_score=0.2):
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 2,
        epa_total=epa, snaps_played=800, games_missed=1,
    )
    p.expected_value = expected_value
    p.risk_score = risk_score
    return p


@pytest.fixture
def simple_roster():
    return [
        _make_player("QB",   30_000_000, 27, "Purdy"),
        _make_player("WR",   20_000_000, 26, "Aiyuk"),
        _make_player("RB",   10_000_000, 25, "CMC"),
        _make_player("OT",   15_000_000, 30, "Williams"),
        _make_player("EDGE", 12_000_000, 28, "Bosa"),
    ]


def test_position_groups_has_eight_keys():
    assert set(POSITION_GROUPS.keys()) == {
        "QB", "SKILL", "OL", "EDGE", "DL", "LB", "DB", "SPECIAL"
    }


def test_position_allocation_sums_to_100(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation(simple_roster)
    total = sum(result.values())
    assert abs(total - 100.0) < 0.01


def test_position_allocation_empty_roster():
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation([])
    assert all(v == 0.0 for v in result.values())


def test_position_allocation_groups_skill_positions(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_position_allocation(simple_roster)
    total_cap = 30 + 20 + 10 + 15 + 12  # millions
    expected_skill = (20 + 10) / total_cap * 100  # WR + RB
    assert abs(result["SKILL"] - expected_skill) < 0.01


def test_position_allocation_skips_blank_position():
    analyzer = SuperBowlTemplateAnalyzer()
    blank = _make_player("", 10_000_000, 25, "Unknown")
    known = _make_player("QB", 30_000_000, 27, "Purdy")
    result = analyzer.calculate_position_allocation([blank, known])
    assert result["QB"] == 100.0


def test_age_distribution_sums_to_100(simple_roster):
    analyzer = SuperBowlTemplateAnalyzer()
    result = analyzer.calculate_age_distribution(simple_roster)
    assert abs(sum(result.values()) - 100.0) < 0.01


def test_age_distribution_correct_buckets():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [
        _make_player("QB", 10_000_000, 23),
        _make_player("WR", 10_000_000, 24),
        _make_player("RB", 10_000_000, 27),
        _make_player("OT", 10_000_000, 32),
    ]
    result = analyzer.calculate_age_distribution(roster)
    assert abs(result["22-25"] - 50.0) < 0.01
    assert abs(result["26-29"] - 25.0) < 0.01
    assert abs(result["30+"]   - 25.0) < 0.01


def test_age_distribution_excludes_age_zero():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [
        _make_player("QB", 10_000_000, 0),
        _make_player("WR", 10_000_000, 25),
    ]
    result = analyzer.calculate_age_distribution(roster)
    assert abs(result["22-25"] - 100.0) < 0.01


def test_star_concentration_top5_leq_top10():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", float(i) * 1_000_000, 25) for i in range(1, 16)]
    result = analyzer.calculate_star_concentration(roster)
    assert result["top_5"] <= result["top_10"]


def test_star_concentration_correct_values():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", float(i) * 1_000_000, 25, f"P{i}") for i in range(1, 11)]
    result = analyzer.calculate_star_concentration(roster)
    total = sum(range(1, 11)) * 1_000_000
    top5 = sum(range(6, 11)) * 1_000_000
    assert abs(result["top_5"] - top5 / total * 100) < 0.01


def test_build_sb_template_keys():
    analyzer = SuperBowlTemplateAnalyzer()
    template = analyzer.build_sb_template()
    assert set(template.keys()) == {"position_allocation", "age_distribution", "star_concentration"}
    assert set(template["position_allocation"].keys()) == {
        "QB", "SKILL", "OL", "EDGE", "DL", "LB", "DB", "SPECIAL"
    }
    assert set(template["age_distribution"].keys()) == {"22-25", "26-29", "30+"}
    assert set(template["star_concentration"].keys()) == {"top_5", "top_10"}


def test_build_sb_template_position_sums_to_100():
    analyzer = SuperBowlTemplateAnalyzer()
    template = analyzer.build_sb_template()
    assert abs(sum(template["position_allocation"].values()) - 100.0) < 0.01


def test_similarity_score_keys():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    assert set(result.keys()) == {
        "position_similarity", "age_similarity", "concentration_similarity",
        "overall_similarity", "gaps",
    }


def test_similarity_score_range():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    for key in ("position_similarity", "age_similarity", "concentration_similarity", "overall_similarity"):
        assert 0.0 <= result[key] <= 100.0


def test_similarity_score_gaps_is_list_of_strings():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    assert isinstance(result["gaps"], list)
    assert all(isinstance(g, str) for g in result["gaps"])


def test_similarity_overall_weighted_correctly():
    analyzer = SuperBowlTemplateAnalyzer()
    roster = [_make_player("QB", 30_000_000, 27)]
    result = analyzer.calculate_similarity_score(roster)
    expected = (
        0.50 * result["position_similarity"] +
        0.30 * result["age_similarity"] +
        0.20 * result["concentration_similarity"]
    )
    assert abs(result["overall_similarity"] - expected) < 0.01
