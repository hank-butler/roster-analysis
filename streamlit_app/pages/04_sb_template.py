import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

from typing import Dict, List

import pandas as pd
import streamlit as st

from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer
from src.visualizations import plot_sb_similarity_radar
from streamlit_app.utils import load_players

st.title("Super Bowl Template Matching")
st.caption(
    "How does the Denver Broncos roster structure compare to recent Super Bowl winners "
    "(2020–2024) across cap allocation, age distribution, and star concentration?"
)

AFC_WEST = {"DEN", "KC", "LAC", "LV"}

players: List[PlayerAsset] = load_players()
teams_data: Dict[str, List[PlayerAsset]] = {}
for p in players:
    if p.team in AFC_WEST:
        teams_data.setdefault(p.team, []).append(p)

den_players = teams_data.get("DEN", [])
if not den_players:
    st.warning("No DEN player data found.")
    st.stop()

sb_analyzer = SuperBowlTemplateAnalyzer()
sim = sb_analyzer.calculate_similarity_score(den_players)
template = sb_analyzer.build_sb_template()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Position Similarity", f"{sim['position_similarity']:.1f}/100")
col2.metric("Age Similarity", f"{sim['age_similarity']:.1f}/100")
col3.metric("Star Concentration", f"{sim['concentration_similarity']:.1f}/100")
col4.metric("Overall Similarity", f"{sim['overall_similarity']:.1f}/100")

st.divider()

st.subheader("Structural Gaps vs SB Template")
if sim["gaps"]:
    for gap in sim["gaps"]:
        st.warning(gap)
else:
    st.success("DEN roster closely matches SB template structure")

st.divider()

st.subheader("SB Similarity Radar — AFC West")
st.plotly_chart(
    plot_sb_similarity_radar(teams_data, template),
    use_container_width=True,
)

st.divider()

st.subheader("SB Template Reference (2020–2024 Averages)")
col_pos, col_age, col_conc = st.columns(3)

with col_pos:
    st.markdown("**Cap by Position Group**")
    pos_df = pd.DataFrame(
        [{"Group": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["position_allocation"].items()]
    )
    st.table(pos_df)

with col_age:
    st.markdown("**Age Distribution**")
    age_df = pd.DataFrame(
        [{"Bucket": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["age_distribution"].items()]
    )
    st.table(age_df)

with col_conc:
    st.markdown("**Star Concentration**")
    conc_df = pd.DataFrame(
        [{"Group": k, "SB Avg %": f"{v:.0f}%"}
         for k, v in template["star_concentration"].items()]
    )
    st.table(conc_df)
