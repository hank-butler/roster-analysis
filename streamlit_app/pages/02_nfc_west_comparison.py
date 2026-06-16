from typing import Dict, List

import streamlit as st

from src.nfc_west_comparison import DivisionAnalyzer
from src.player_valuation import PlayerAsset
from streamlit_app.utils import load_players

st.title("NFC West — Division Comparison")

NFC_WEST = {"SF", "SEA", "LAR", "ARI"}

players: List[PlayerAsset] = load_players()
teams_data: Dict[str, List[PlayerAsset]] = {}
for p in players:
    if p.team in NFC_WEST:
        teams_data.setdefault(p.team, []).append(p)

if not teams_data:
    st.warning("No NFC West player data found.")
    st.stop()

with st.spinner("Building division analysis..."):
    analyzer = DivisionAnalyzer(teams_data)
    report = analyzer.generate_division_report(primary_team="SF")

st.subheader("Portfolio Metrics by Team")
metrics_df = report["metrics_df"].sort_values("efficiency", ascending=False)
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(
        report["figures"]["efficiency_scatter"], use_container_width=True
    )
with col2:
    st.plotly_chart(
        report["figures"]["position_allocation"], use_container_width=True
    )

st.divider()

st.subheader("SF Division Advantages")
advantages = report["advantages"]

col_s, col_w, col_o = st.columns(3)

with col_s:
    st.markdown("**Strengths** (SF leads division avg)")
    if advantages["strengths"]:
        for pos in advantages["strengths"]:
            st.success(pos)
    else:
        st.caption("No position groups where SF leads")

with col_w:
    st.markdown("**Weaknesses** (SF trails division avg)")
    if advantages["weaknesses"]:
        for pos in advantages["weaknesses"]:
            st.warning(pos)
    else:
        st.caption("No position groups where SF trails")

with col_o:
    st.markdown("**Opportunities** (weaknesses where SF ranks 3rd/4th)")
    if advantages["opportunities"]:
        for pos in advantages["opportunities"]:
            st.info(pos)
    else:
        st.caption("No high-priority opportunities identified")
