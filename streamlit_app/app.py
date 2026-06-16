import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # project root

from typing import List

import streamlit as st

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.sb_template import SuperBowlTemplateAnalyzer
from streamlit_app.utils import load_players

st.set_page_config(
    page_title="SF 49ers Football AI",
    page_icon="🏈",
    layout="wide",
)

st.title("SF 49ers Football AI System")
st.caption(
    "An AI-powered football intelligence system that uses generative AI and "
    "multi-agent workflows to automate scouting reports, answer natural language "
    "roster questions, and evolve optimal roster configurations within hard "
    "cap constraints."
)

players: List[PlayerAsset] = load_players()
sf_players = [p for p in players if p.team == "SF"]

if not sf_players:
    st.warning("No SF players loaded — check data/processed/player_assets_ready.csv")
    st.stop()

pa = PortfolioAnalyzer(sf_players)
sim = SuperBowlTemplateAnalyzer().calculate_similarity_score(sf_players)

col1, col2, col3, col4 = st.columns(4)
col1.metric("SF Players", len(sf_players))
col2.metric("Portfolio Efficiency", f"{pa.portfolio_efficiency():.2f}x")
col3.metric("Portfolio Risk", f"{pa.portfolio_risk():.2f}")
col4.metric("SB Similarity", f"{sim['overall_similarity']:.1f}/100")

st.divider()

st.markdown("### Built Systems")
st.markdown("""
- **Roster Valuation** — Bond-pricing model assigns fair value, efficiency ratio,
  and Sharpe ratio to every player contract
- **NFC West Comparison** — Division-wide portfolio analysis powered by DivisionAnalyzer
- **Evolution Engine** — Genetic algorithm finds optimal 53-man rosters within
  hard cap constraints
- **SB Template Matching** — Scores each roster against Super Bowl winner averages
  (2020–2024) across position allocation, age, and star concentration
- **AI Football Intelligence** — Multi-agent system (Contract / Scouting / Strategy)
  answers natural language roster questions grounded in real data
""")

st.info("Use the sidebar to navigate between pages.")
