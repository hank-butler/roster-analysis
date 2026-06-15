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
            "player_name": "George Kittle", "position": "TE", "team": "SF", "age": 31,
            "cap_hit": 10_900_000.0, "total_value": 75_000_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 12.9, "snaps_played": 2400, "games_missed": 4,
        },
        {
            "player_name": "Trent Williams", "position": "OT", "team": "SF", "age": 36,
            "cap_hit": 20_000_000.0, "total_value": 0.0,
            "guaranteed_money": 5_000_000.0, "years_remaining": 1,
            "epa_total": np.nan, "snaps_played": np.nan, "games_missed": np.nan,
        },
        {
            "player_name": "Brock Purdy", "position": "QB", "team": "SF", "age": 26,
            "cap_hit": 37_750_000.0, "total_value": 244_200_000.0,
            "guaranteed_money": 0.0, "years_remaining": 1,
            "epa_total": 35.0, "snaps_played": 2050, "games_missed": 0,
        },
    ])


def test_compute_features_fills_null_epa_with_positional_average(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    williams = result[result["player_name"] == "Trent Williams"].iloc[0]
    # OT position has no other matched players, falls back to global average of Kittle+Purdy
    assert not pd.isna(williams["epa_total"])
    assert not pd.isna(williams["snaps_played"])
    assert not pd.isna(williams["games_missed"])


def test_compute_features_does_not_alter_matched_players(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    kittle = result[result["player_name"] == "George Kittle"].iloc[0]
    assert kittle["epa_total"] == 12.9
    assert kittle["snaps_played"] == 2400
    assert kittle["games_missed"] == 4


def test_compute_features_global_fallback_is_average_of_matched(sample_merged):
    processor = DataProcessor()
    result = processor.compute_features(sample_merged)
    williams = result[result["player_name"] == "Trent Williams"].iloc[0]
    # Global average of matched players (Kittle: 12.9, Purdy: 35.0) = 23.95
    expected_epa = (12.9 + 35.0) / 2
    assert abs(williams["epa_total"] - expected_epa) < 0.1


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
    purdy = next(a for a in assets if "Purdy" in a.name)
    assert isinstance(purdy.cap_hit_2026, float)
    assert isinstance(purdy.age, int)
    assert isinstance(purdy.snaps_played, int)
    assert isinstance(purdy.games_missed, int)
