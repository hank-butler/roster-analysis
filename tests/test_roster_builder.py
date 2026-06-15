import pytest
import pandas as pd
import numpy as np
from src.data_collection.roster_builder import RosterBuilder


@pytest.fixture
def sample_stats() -> pd.DataFrame:
    """Three-season stats — columns match actual nfl_data_py structure (no player_name/team)."""
    return pd.DataFrame([
        {"player_id": "k001", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 12.0, "offense_snaps": 800},
        {"player_id": "k001", "season": 2024, "games": 14,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 10.0, "offense_snaps": 700},
        {"player_id": "k001", "season": 2025, "games": 17,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 15.0, "offense_snaps": 900},
        {"player_id": "p001", "season": 2024, "games": 16,
         "passing_epa": 30.0, "rushing_epa": 2.0, "receiving_epa": 0.0, "offense_snaps": 1000},
        {"player_id": "p001", "season": 2025, "games": 17,
         "passing_epa": 35.0, "rushing_epa": 3.0, "receiving_epa": 0.0, "offense_snaps": 1050},
    ])


@pytest.fixture
def sample_rosters() -> pd.DataFrame:
    """Roster data — provides player_name, position, team for each player_id + season."""
    return pd.DataFrame([
        {"player_id": "k001", "season": 2023, "player_name": "George Kittle",
         "position": "TE", "team": "SF"},
        {"player_id": "k001", "season": 2024, "player_name": "George Kittle",
         "position": "TE", "team": "SF"},
        {"player_id": "k001", "season": 2025, "player_name": "George Kittle",
         "position": "TE", "team": "SF"},
        {"player_id": "p001", "season": 2024, "player_name": "Brock Purdy",
         "position": "QB", "team": "SF"},
        {"player_id": "p001", "season": 2025, "player_name": "Brock Purdy",
         "position": "QB", "team": "SF"},
    ])


@pytest.fixture
def sample_contracts() -> pd.DataFrame:
    return pd.DataFrame([
        {"player_name": "George Kittle", "position": np.nan, "team": "SF",
         "cap_hit": 10_900_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 31},
        {"player_name": "Brock Purdy", "position": np.nan, "team": "SF",
         "cap_hit": 37_750_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 26},
        {"player_name": "Brandon Aiyuk", "position": np.nan, "team": "SF",
         "cap_hit": 24_900_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 27},
    ])


def test_epa_weighted_decay_three_seasons(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 2023: 12 * 0.2 = 2.4, 2024: 10 * 0.3 = 3.0, 2025: 15 * 0.5 = 7.5 → total = 12.9
    assert abs(kittle["epa_total"] - 12.9) < 0.01


def test_epa_prorated_when_seasons_missing(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    purdy = agg[agg["player_name"] == "Brock Purdy"].iloc[0]
    # Only 2024 and 2025. Prorated: 2024=0.3/0.8, 2025=0.5/0.8
    expected = 32.0 * (0.3 / 0.8) + 38.0 * (0.5 / 0.8)
    assert abs(purdy["epa_total"] - expected) < 0.01


def test_games_missed_raw_sum(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 2023: 17-16=1, 2024: 17-14=3, 2025: 17-17=0 → total = 4
    assert kittle["games_missed"] == 4


def test_snaps_raw_sum(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    kittle = agg[agg["player_name"] == "George Kittle"].iloc[0]
    # 800 + 700 + 900 = 2400
    assert kittle["snaps_played"] == 2400


def test_merge_matches_on_name_and_team(sample_stats, sample_rosters, sample_contracts):
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    merged = builder.merge(perf, sample_contracts)
    kittle = merged[merged["player_name"] == "George Kittle"]
    assert len(kittle) == 1
    assert kittle.iloc[0]["cap_hit"] == 10_900_000.0
    assert abs(kittle.iloc[0]["epa_total"] - 12.9) < 0.01


def test_unmatched_player_included_with_nulls(sample_stats, sample_rosters, sample_contracts):
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    merged = builder.merge(perf, sample_contracts)
    aiyuk = merged[merged["player_name"] == "Brandon Aiyuk"]
    assert len(aiyuk) == 1
    assert pd.isna(aiyuk.iloc[0]["epa_total"])


def test_unmatched_log_written(sample_stats, sample_rosters, sample_contracts, tmp_path):
    builder = RosterBuilder(output_dir=str(tmp_path))
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    builder.merge(perf, sample_contracts)
    unmatched_path = tmp_path / "unmatched_players.csv"
    assert unmatched_path.exists()
    unmatched = pd.read_csv(unmatched_path)
    assert "Brandon Aiyuk" in unmatched["otc_name"].values
