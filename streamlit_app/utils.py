from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from src.player_valuation import PlayerAsset, PlayerValuationModel

_CSV_PATH = (
    Path(__file__).parent.parent / "data" / "processed" / "player_assets_ready.csv"
)


def _load_players_from_csv(csv_path: str) -> List[PlayerAsset]:
    """Load and value players from a CSV file. Pure function — no Streamlit calls.

    Separated from the cached wrapper so it can be unit-tested directly.

    Args:
        csv_path: Absolute path to player_assets_ready.csv.

    Returns:
        List of valued PlayerAsset objects.

    Raises:
        FileNotFoundError: If the CSV does not exist.
    """
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Run: python collect_all_data.py"
        )
    df = pd.read_csv(p)
    players: List[PlayerAsset] = []
    for _, row in df.iterrows():
        try:
            players.append(
                PlayerAsset(
                    player_id=str(row["player_id"]),
                    name=str(row["name"]),
                    position=str(row["position"]),
                    team=str(row["team"]),
                    age=int(row["age"]),
                    cap_hit_2026=float(row["cap_hit_2026"]),
                    years_remaining=int(row["years_remaining"]),
                    guaranteed_money=float(row["guaranteed_money"]),
                    total_contract_value=float(row["total_contract_value"]),
                    epa_total=float(row["epa_total"]),
                    snaps_played=int(row["snaps_played"]),
                    games_missed=int(row["games_missed"]),
                )
            )
        except Exception:
            continue

    model = PlayerValuationModel()
    return model.value_roster(players)


@st.cache_data
def load_players() -> List[PlayerAsset]:
    """Load and value all players from the processed CSV.

    Cached by Streamlit for the duration of the session — the CSV load and
    PlayerValuationModel.value_roster() run exactly once regardless of how
    many pages are visited.

    Returns:
        List of valued PlayerAsset objects.
    """
    try:
        return _load_players_from_csv(str(_CSV_PATH))
    except FileNotFoundError as exc:
        st.error(f"Data not found: {exc}")
        st.stop()
        return []  # unreachable; satisfies type checker
