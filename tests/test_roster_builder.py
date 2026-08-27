import pytest
import pandas as pd
import numpy as np
from src.data_collection.roster_builder import RosterBuilder


@pytest.fixture
def sample_stats() -> pd.DataFrame:
    """Three-season stats — columns match actual nfl_data_py structure (no player_name/team)."""
    return pd.DataFrame([
        {"player_id": "e001", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 12.0, "offense_snaps": 800},
        {"player_id": "e001", "season": 2024, "games": 14,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 10.0, "offense_snaps": 700},
        {"player_id": "e001", "season": 2025, "games": 17,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 15.0, "offense_snaps": 900},
        {"player_id": "n001", "season": 2024, "games": 16,
         "passing_epa": 30.0, "rushing_epa": 2.0, "receiving_epa": 0.0, "offense_snaps": 1000},
        {"player_id": "n001", "season": 2025, "games": 17,
         "passing_epa": 35.0, "rushing_epa": 3.0, "receiving_epa": 0.0, "offense_snaps": 1050},
    ])


@pytest.fixture
def sample_rosters() -> pd.DataFrame:
    """Roster data — provides player_name, position, team for each player_id + season."""
    return pd.DataFrame([
        {"player_id": "e001", "season": 2023, "player_name": "Evan Engram",
         "position": "TE", "team": "DEN"},
        {"player_id": "e001", "season": 2024, "player_name": "Evan Engram",
         "position": "TE", "team": "DEN"},
        {"player_id": "e001", "season": 2025, "player_name": "Evan Engram",
         "position": "TE", "team": "DEN"},
        {"player_id": "n001", "season": 2024, "player_name": "Bo Nix",
         "position": "QB", "team": "DEN"},
        {"player_id": "n001", "season": 2025, "player_name": "Bo Nix",
         "position": "QB", "team": "DEN"},
    ])


@pytest.fixture
def sample_contracts() -> pd.DataFrame:
    return pd.DataFrame([
        {"player_name": "Evan Engram", "position": np.nan, "team": "DEN",
         "cap_hit": 10_900_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 31},
        {"player_name": "Bo Nix", "position": np.nan, "team": "DEN",
         "cap_hit": 37_750_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 26},
        {"player_name": "Courtland Sutton", "position": np.nan, "team": "DEN",
         "cap_hit": 24_900_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 27},
    ])


def test_epa_weighted_decay_three_seasons(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    engram = agg[agg["player_name"] == "Evan Engram"].iloc[0]
    # Weighted avg: 2023: 12*0.2=2.4, 2024: 10*0.3=3.0, 2025: 15*0.5=7.5 → 12.9
    # Normalised by 3 seasons → 12.9 / 3 = 4.3
    assert abs(engram["epa_total"] - 4.3) < 0.01


def test_epa_prorated_when_seasons_missing(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    nix = agg[agg["player_name"] == "Bo Nix"].iloc[0]
    # Only 2024 and 2025. Prorated: 2024=0.3/0.8, 2025=0.5/0.8
    # Weighted avg = 32.0*(0.3/0.8) + 38.0*(0.5/0.8) = 35.75
    # Normalised by 2 seasons → 35.75 / 2 = 17.875
    expected = (32.0 * (0.3 / 0.8) + 38.0 * (0.5 / 0.8)) / 2
    assert abs(nix["epa_total"] - expected) < 0.01


def test_games_missed_per_season(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    engram = agg[agg["player_name"] == "Evan Engram"].iloc[0]
    # Raw total: 2023: 17-16=1, 2024: 17-14=3, 2025: 17-17=0 → 4 over 3 seasons
    # Per-season average: int(4 / 3) = 1
    assert engram["games_missed"] == 1


def test_snaps_per_season(sample_stats, sample_rosters):
    builder = RosterBuilder()
    agg = builder._aggregate_performance(sample_stats, sample_rosters)
    engram = agg[agg["player_name"] == "Evan Engram"].iloc[0]
    # Raw total: 800 + 700 + 900 = 2400 over 3 seasons
    # Per-season average: int(2400 / 3) = 800
    assert engram["snaps_played"] == 800


def test_merge_matches_on_name_and_team(sample_stats, sample_rosters, sample_contracts):
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    merged = builder.merge(perf, sample_contracts)
    engram = merged[merged["player_name"] == "Evan Engram"]
    assert len(engram) == 1
    assert engram.iloc[0]["cap_hit"] == 10_900_000.0
    assert abs(engram.iloc[0]["epa_total"] - 4.3) < 0.01  # 12.9 / 3 seasons


def test_unmatched_player_included_with_nulls(sample_stats, sample_rosters, sample_contracts):
    builder = RosterBuilder()
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    merged = builder.merge(perf, sample_contracts)
    sutton = merged[merged["player_name"] == "Courtland Sutton"]
    assert len(sutton) == 1
    assert pd.isna(sutton.iloc[0]["epa_total"])


def test_unmatched_log_written(sample_stats, sample_rosters, sample_contracts, tmp_path):
    builder = RosterBuilder(output_dir=str(tmp_path))
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    builder.merge(perf, sample_contracts)
    unmatched_path = tmp_path / "unmatched_players.csv"
    assert unmatched_path.exists()
    unmatched = pd.read_csv(unmatched_path)
    assert "Courtland Sutton" in unmatched["otc_name"].values


def test_load_contract_data_drops_top_51_cutoff_row(tmp_path):
    """OTC-scraped CSVs contain a 'Top 51 Cutoff' table-label row that must be dropped."""
    contract_dir = tmp_path / "contracts"
    contract_dir.mkdir()
    pd.DataFrame([
        {"player_name": "Bo Nix", "position": np.nan, "team": "DEN",
         "cap_hit": 5_000_000.0, "guaranteed_money": 0.0, "years_remaining": 3, "age": 26},
        {"player_name": "Top 51 Cutoff", "position": np.nan, "team": "DEN",
         "cap_hit": 0.0, "guaranteed_money": 0.0, "years_remaining": 0, "age": np.nan},
    ]).to_csv(contract_dir / "den_2026.csv", index=False)

    builder = RosterBuilder(contract_dir=str(contract_dir), output_dir=str(tmp_path))
    result = builder.load_contract_data(["DEN"])

    assert "Top 51 Cutoff" not in result["player_name"].str.strip().values
    assert len(result) == 1


def test_build_afc_west_writes_afc_west_rosters_csv(tmp_path, monkeypatch):
    builder = RosterBuilder(output_dir=str(tmp_path))
    perf_stub = pd.DataFrame([{
        "player_name": "Bo Nix", "team": "DEN", "position": "QB",
        "age": 26, "epa_total": 10.0, "snaps_played": 900, "games_missed": 0,
    }])
    contract_stub = pd.DataFrame([{
        "player_name": "Bo Nix", "position": np.nan, "team": "DEN",
        "cap_hit": 5_000_000.0, "guaranteed_money": 0.0, "years_remaining": 3, "age": 26,
    }])
    captured_teams = {}

    def fake_load_contract_data(teams):
        captured_teams["teams"] = teams
        return contract_stub

    monkeypatch.setattr(builder, "load_performance_data", lambda: perf_stub)
    monkeypatch.setattr(builder, "load_contract_data", fake_load_contract_data)

    result = builder.build_afc_west()

    assert captured_teams["teams"] == ["DEN", "KC", "LAC", "LV"]
    output_path = tmp_path / "afc_west_rosters.csv"
    assert output_path.exists()
    assert "Bo Nix" in result["player_name"].values
