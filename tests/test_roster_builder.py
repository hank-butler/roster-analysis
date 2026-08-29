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


def test_merge_matches_on_name_and_team(sample_stats, sample_rosters, sample_contracts, tmp_path):
    builder = RosterBuilder(output_dir=str(tmp_path))
    perf = builder._aggregate_performance(sample_stats, sample_rosters)
    merged = builder.merge(perf, sample_contracts)
    engram = merged[merged["player_name"] == "Evan Engram"]
    assert len(engram) == 1
    assert engram.iloc[0]["cap_hit"] == 10_900_000.0
    assert abs(engram.iloc[0]["epa_total"] - 4.3) < 0.01  # 12.9 / 3 seasons


def test_unmatched_player_included_with_nulls(sample_stats, sample_rosters, sample_contracts, tmp_path):
    builder = RosterBuilder(output_dir=str(tmp_path))
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


def test_build_sb_winners_writes_own_unmatched_file(tmp_path, monkeypatch):
    """build_sb_winners() must not clobber unmatched_players.csv written by
    build_afc_west() — it should write to unmatched_sb_winners.csv instead."""
    builder = RosterBuilder(output_dir=str(tmp_path))

    afc_perf_stub = pd.DataFrame([{
        "player_name": "Bo Nix", "team": "DEN", "position": "QB",
        "age": 26, "epa_total": 10.0, "snaps_played": 900, "games_missed": 0,
    }])
    afc_contract_stub = pd.DataFrame([
        {"player_name": "Bo Nix", "position": np.nan, "team": "DEN",
         "cap_hit": 5_000_000.0, "guaranteed_money": 0.0, "years_remaining": 3, "age": 26},
        {"player_name": "Some Unmatched AFC Player", "position": np.nan, "team": "DEN",
         "cap_hit": 1_000_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 24},
    ])
    sb_perf_stub = pd.DataFrame([{
        "player_name": "Patrick Mahomes", "team": "KC", "position": "QB",
        "age": 30, "epa_total": 50.0, "snaps_played": 1000, "games_missed": 0,
    }])
    sb_contract_stub = pd.DataFrame([
        {"player_name": "Patrick Mahomes", "position": np.nan, "team": "KC",
         "cap_hit": 45_000_000.0, "guaranteed_money": 0.0, "years_remaining": 3, "age": 30},
        {"player_name": "Some Unmatched SB Player", "position": np.nan, "team": "KC",
         "cap_hit": 1_000_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": 24},
    ])

    def fake_load_performance_data():
        # First call is for build_afc_west, second for build_sb_winners
        if not hasattr(fake_load_performance_data, "calls"):
            fake_load_performance_data.calls = 0
        fake_load_performance_data.calls += 1
        return afc_perf_stub if fake_load_performance_data.calls == 1 else sb_perf_stub

    def fake_load_contract_data(teams):
        return afc_contract_stub if "DEN" in teams else sb_contract_stub

    monkeypatch.setattr(builder, "load_performance_data", fake_load_performance_data)
    monkeypatch.setattr(builder, "load_contract_data", fake_load_contract_data)

    builder.build_afc_west()
    builder.build_sb_winners()

    afc_unmatched_path = tmp_path / "unmatched_players.csv"
    sb_unmatched_path = tmp_path / "unmatched_sb_winners.csv"
    assert afc_unmatched_path.exists()
    assert sb_unmatched_path.exists()

    afc_unmatched = pd.read_csv(afc_unmatched_path)
    sb_unmatched = pd.read_csv(sb_unmatched_path)

    assert "Some Unmatched AFC Player" in afc_unmatched["otc_name"].values
    assert "Some Unmatched SB Player" not in afc_unmatched["otc_name"].values
    assert "Some Unmatched SB Player" in sb_unmatched["otc_name"].values
    assert "Some Unmatched AFC Player" not in sb_unmatched["otc_name"].values


def test_position_and_age_backfill_uses_name_only_fallback_across_teams(tmp_path):
    """A contract row whose player appears in rosters under a DIFFERENT team
    (e.g. traded/signed elsewhere) should still get position and age backfilled
    via a name-only fallback, as long as the name is unambiguous league-wide."""
    rosters_df = pd.DataFrame([
        {"player_id": "w001", "season": 2023, "player_name": "Jaylen Waddle",
         "position": "WR", "team": "MIA", "birth_date": "1998-11-25"},
        {"player_id": "w001", "season": 2024, "player_name": "Jaylen Waddle",
         "position": "WR", "team": "MIA", "birth_date": "1998-11-25"},
    ])
    perf_dir = tmp_path / "perf"
    perf_dir.mkdir()
    rosters_df.to_csv(perf_dir / "rosters_2023_2025.csv", index=False)

    stats_df = pd.DataFrame([
        {"player_id": "w001", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 20.0, "offense_snaps": 700},
    ])

    builder = RosterBuilder(perf_dir=str(perf_dir), output_dir=str(tmp_path))
    perf = builder._aggregate_performance(stats_df, rosters_df)

    # Contract row lists Waddle under DEN (a team he never actually played for in
    # rosters_df) — simulates an OTC scrape row for a different-team player whose
    # (name, team) key can't be found, but whose name is unambiguous league-wide.
    contracts = pd.DataFrame([
        {"player_name": "Jaylen Waddle", "position": np.nan, "team": "DEN",
         "cap_hit": 1_000_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": np.nan},
    ])

    merged = builder.merge(perf, contracts)
    row = merged[merged["player_name"] == "Jaylen Waddle"].iloc[0]

    assert str(row["position"]).strip() == "WR"
    assert int(row["age"]) == 2026 - 1998


def test_position_fallback_drops_ambiguous_name_across_teams(tmp_path):
    """A name that appears in rosters data under TWO different teams with TWO
    different positions must not be backfilled via the name-only fallback —
    it's ambiguous which position belongs to the OTC contract row's player,
    so the merged row's position should stay empty."""
    rosters_df = pd.DataFrame([
        {"player_id": "h001", "season": 2023, "player_name": "Marvin Harrison",
         "position": "WR", "team": "IND", "birth_date": "2001-01-01"},
        {"player_id": "h002", "season": 2023, "player_name": "Marvin Harrison",
         "position": "CB", "team": "SEA", "birth_date": "1998-01-01"},
    ])
    perf_dir = tmp_path / "perf"
    perf_dir.mkdir()
    rosters_df.to_csv(perf_dir / "rosters_2023_2025.csv", index=False)

    stats_df = pd.DataFrame([
        {"player_id": "h001", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 10.0, "offense_snaps": 500},
        {"player_id": "h002", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 0.0, "offense_snaps": 500},
    ])

    builder = RosterBuilder(perf_dir=str(perf_dir), output_dir=str(tmp_path))
    perf = builder._aggregate_performance(stats_df, rosters_df)

    # Contract row lists the player under DEN — a team not present in rosters_df
    # for this name — so both the (name, team) position lookup and the perf
    # fuzzy match miss, forcing a fall-through to the name-only lookup, which
    # must refuse to resolve because the name maps to WR under IND and CB
    # under SEA.
    contracts = pd.DataFrame([
        {"player_name": "Marvin Harrison", "position": np.nan, "team": "DEN",
         "cap_hit": 1_000_000.0, "guaranteed_money": 0.0, "years_remaining": 1, "age": np.nan},
    ])

    merged = builder.merge(perf, contracts)
    row = merged[merged["player_name"] == "Marvin Harrison"].iloc[0]

    assert str(row["position"]).strip() in ("", "nan")


def test_position_group_conflict_rejects_fuzzy_match(tmp_path):
    """A fuzzy name match must be rejected when the position-lookup group for
    the OTC (name, team) conflicts with the position group of the matched
    perf row — e.g. Brandon Jones (a DB) must not fuzzy-match Brandon
    Johnson's WR perf row just because the names are similar."""
    rosters_df = pd.DataFrame([
        {"player_id": "j001", "season": 2024, "player_name": "Brandon Jones",
         "position": "DB", "team": "DEN", "birth_date": "1998-04-02"},
        {"player_id": "j001", "season": 2025, "player_name": "Brandon Jones",
         "position": "DB", "team": "DEN", "birth_date": "1998-04-02"},
        {"player_id": "j002", "season": 2023, "player_name": "Brandon Johnson",
         "position": "WR", "team": "DEN", "birth_date": "1998-07-26"},
        {"player_id": "j002", "season": 2025, "player_name": "Brandon Johnson",
         "position": "WR", "team": "DEN", "birth_date": "1998-07-26"},
    ])
    perf_dir = tmp_path / "perf"
    perf_dir.mkdir()
    rosters_df.to_csv(perf_dir / "rosters_2023_2025.csv", index=False)

    # Only Brandon Johnson (WR) has stat rows -- DBs typically lack passing/
    # rushing/receiving EPA in nfl_data_py's seasonal stats, which is exactly
    # why the buggy fuzzy match only ever found Johnson as a same-team
    # candidate for the Jones contract row.
    stats_df = pd.DataFrame([
        {"player_id": "j002", "season": 2023, "games": 16,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 20.0, "offense_snaps": 650},
        {"player_id": "j002", "season": 2025, "games": 17,
         "passing_epa": 0.0, "rushing_epa": 0.0, "receiving_epa": 22.0, "offense_snaps": 700},
    ])

    builder = RosterBuilder(perf_dir=str(perf_dir), output_dir=str(tmp_path))
    perf = builder._aggregate_performance(stats_df, rosters_df)

    contracts = pd.DataFrame([
        {"player_name": "Brandon Jones", "position": np.nan, "team": "DEN",
         "cap_hit": 6_990_000.0, "guaranteed_money": 1_833_334.0,
         "years_remaining": 1, "age": np.nan},
    ])

    merged = builder.merge(perf, contracts)
    row = merged[merged["player_name"] == "Brandon Jones"].iloc[0]

    # Position must come from the lookup (DB), not from the rejected WR match.
    assert str(row["position"]).strip() == "DB"
    # Performance fields must be NaN since the match was rejected.
    assert pd.isna(row["epa_total"])


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
