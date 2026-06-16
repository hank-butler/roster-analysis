import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

from typing import List

import streamlit as st

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.visualizations import plot_player_value_scatter
from streamlit_app.utils import load_players

st.title("SF 49ers — Roster Valuation")

players: List[PlayerAsset] = load_players()
sf_players = [p for p in players if p.team == "SF"]

if not sf_players:
    st.warning("No SF players loaded.")
    st.stop()

pa = PortfolioAnalyzer(sf_players)
summary = pa.summary_report()

col1, col2, col3 = st.columns(3)
col1.metric("Portfolio Efficiency", f"{summary['efficiency']:.2f}x")
col2.metric("Portfolio Risk", f"{summary['risk']:.2f}")
col3.metric("Sharpe Ratio", f"{summary['sharpe_ratio']:.2f}")

st.subheader("Player Value vs Cap Hit")
st.caption(
    "Green = undervalued (value > cap × 1.15)  |  "
    "Red = overvalued (cap > value × 1.15)  |  "
    "Size = inversely proportional to risk score"
)
st.plotly_chart(
    plot_player_value_scatter(sf_players, highlight_team="SF"),
    use_container_width=True,
)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Most Overvalued")
    ov = pa.identify_overvalued().head(5)
    if ov.empty:
        st.success("No significantly overvalued players")
    else:
        st.dataframe(
            ov[["name", "position", "cap_hit", "fair_value", "pct_overvalued"]],
            use_container_width=True,
            hide_index=True,
        )

with col_right:
    st.subheader("Most Undervalued")
    uv = pa.identify_undervalued().head(5)
    if uv.empty:
        st.success("No significantly undervalued players")
    else:
        st.dataframe(
            uv[["name", "position", "cap_hit", "fair_value", "pct_undervalued"]],
            use_container_width=True,
            hide_index=True,
        )
