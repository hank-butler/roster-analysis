import pandas as pd
import pytest
from src.player_valuation import PlayerAsset


def test_load_players_from_csv_returns_valued_players(tmp_path):
    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([{
        "player_id": "sf_qb_test", "name": "Test QB", "position": "QB",
        "team": "DEN", "age": 27, "cap_hit_2026": 23_700_000,
        "years_remaining": 3, "guaranteed_money": 10_000_000,
        "total_contract_value": 71_100_000, "epa_total": 45.0,
        "snaps_played": 1050, "games_missed": 0,
    }]).to_csv(csv_path, index=False)

    from streamlit_app.utils import _load_players_from_csv
    players = _load_players_from_csv(str(csv_path))

    assert len(players) == 1
    assert players[0].name == "Test QB"
    assert players[0].position == "QB"
    assert players[0].expected_value != 0.0  # PlayerValuationModel ran


def test_load_players_from_csv_raises_on_missing_file():
    from streamlit_app.utils import _load_players_from_csv
    with pytest.raises(FileNotFoundError):
        _load_players_from_csv("/nonexistent/path/player_assets_ready.csv")


def test_load_players_from_csv_skips_bad_rows(tmp_path):
    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([
        {
            "player_id": "sf_qb_good", "name": "Good QB", "position": "QB",
            "team": "DEN", "age": 27, "cap_hit_2026": 23_700_000,
            "years_remaining": 3, "guaranteed_money": 10_000_000,
            "total_contract_value": 71_100_000, "epa_total": 45.0,
            "snaps_played": 1050, "games_missed": 0,
        },
        {
            "player_id": "bad_row", "name": "Bad Player", "position": "QB",
            "team": "DEN", "age": "not_a_number",
            "cap_hit_2026": 10_000_000, "years_remaining": 1,
            "guaranteed_money": 0, "total_contract_value": 0,
            "epa_total": 0, "snaps_played": 0, "games_missed": 0,
        },
    ]).to_csv(csv_path, index=False)

    from streamlit_app.utils import _load_players_from_csv
    players = _load_players_from_csv(str(csv_path))
    assert len(players) == 1
    assert players[0].name == "Good QB"
