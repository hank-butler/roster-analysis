import pytest
import pandas as pd
import numpy as np
from src.data_collection.data_processor import DataProcessor
from src.player_valuation import PlayerAsset


@pytest.fixture
def sample_merged() -> pd.DataFrame:
    """Simulates RosterBuilder.merge() output — mixed matched/unmatched players."""
    return pd.DataFrame([
        {
            "player_name": "Evan Engram", "position": "TE", "team": "DEN", "age": 31,
            "cap_hit": 14_136_666.0, "total_value": 41_250_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 12.9, "snaps_played": 2400, "games_missed": 4,
        },
        {
            "player_name": "Garett Bolles", "position": "OT", "team": "DEN", "age": 34,
            "cap_hit": 8_452_000.0, "total_value": 0.0,
            "guaranteed_money": 5_000_000.0, "years_remaining": 1,
            "epa_total": np.nan, "snaps_played": np.nan, "games_missed": np.nan,
        },
        {
            "player_name": "Bo Nix", "position": "QB", "team": "DEN", "age": 26,
            "cap_hit": 5_076_318.0, "total_value": 18_600_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 35.0, "snaps_played": 2050, "games_missed": 0,
        },
    ])


def test_compute_features_fills_null_epa_with_positional_average(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    bolles = result[result["player_name"] == "Garett Bolles"].iloc[0]
    # OT position has no other matched players, falls back to global average of Engram+Nix
    assert not pd.isna(bolles["epa_total"])
    assert not pd.isna(bolles["snaps_played"])
    assert not pd.isna(bolles["games_missed"])


def test_compute_features_does_not_alter_matched_players(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    engram = result[result["player_name"] == "Evan Engram"].iloc[0]
    assert engram["epa_total"] == 12.9
    assert engram["snaps_played"] == 2400
    assert engram["games_missed"] == 4


def test_compute_features_global_fallback_is_average_of_matched(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    bolles = result[result["player_name"] == "Garett Bolles"].iloc[0]
    # Global average of matched players (Engram: 12.9, Nix: 35.0) = 23.95
    expected_epa = (12.9 + 35.0) / 2
    assert abs(bolles["epa_total"] - expected_epa) < 0.1


def test_enforce_schema_renames_columns(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    result = processor.enforce_schema(filled)
    assert "cap_hit_2026" in result.columns
    assert "total_contract_value" in result.columns
    assert "name" in result.columns
    assert "cap_hit" not in result.columns
    assert "total_value" not in result.columns
    assert "player_name" not in result.columns


def test_enforce_schema_generates_player_id(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    result = processor.enforce_schema(filled)
    assert "player_id" in result.columns
    assert result["player_id"].notna().all()
    assert result["player_id"].nunique() == 3


def test_enforce_schema_coerces_integer_types(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    result = processor.enforce_schema(filled)
    assert result["age"].dtype in (int, "int64", "int32")
    assert result["snaps_played"].dtype in (int, "int64", "int32")
    assert result["games_missed"].dtype in (int, "int64", "int32")


def test_to_player_assets_returns_correct_types(sample_merged):
    processor = DataProcessor()
    filled = processor.compute_features(sample_merged)
    schemed = processor.enforce_schema(filled)
    assets = processor.to_player_assets(schemed)
    assert isinstance(assets, list)
    assert all(isinstance(a, PlayerAsset) for a in assets)
    assert len(assets) == 3
    nix = next(a for a in assets if "Nix" in a.name)
    assert isinstance(nix.cap_hit_2026, float)
    assert isinstance(nix.age, int)
    assert isinstance(nix.snaps_played, int)
    assert isinstance(nix.games_missed, int)
