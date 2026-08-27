import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

import os
from typing import List

import streamlit as st

from src.agents import AgentSystem
from src.player_valuation import PlayerAsset
from streamlit_app.utils import load_players

st.title("AI Football Intelligence")
st.caption(
    "Ask natural language questions about the Broncos roster. "
    "Powered by a multi-agent system (Contract · Scouting · Strategy) "
    "grounded in real player data."
)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.warning(
        "No ANTHROPIC_API_KEY environment variable found. "
        "Enter your key below to use the AI assistant."
    )
    api_key = st.text_input(
        "Anthropic API key:",
        type="password",
        placeholder="sk-ant-...",
    )
    if not api_key:
        st.info(
            "Get an API key at https://console.anthropic.com — "
            "or set ANTHROPIC_API_KEY before launching Streamlit."
        )
        st.stop()

st.subheader("Ask a Question")
query = st.text_area(
    "Question:",
    placeholder=(
        "e.g. Who are our most undervalued players?\n"
        "e.g. Generate a scouting report on Patrick Surtain II\n"
        "e.g. How does our cap allocation compare to Super Bowl winners?\n"
        "e.g. Which positions should we target in free agency?"
    ),
    height=100,
)

ask_disabled = not query.strip()
asked = st.button("Ask", disabled=ask_disabled)

st.caption(
    "**Example queries:** 'Who are our most undervalued players?' · "
    "'Generate a scouting report on Patrick Surtain II' · "
    "'How does our cap allocation compare to Super Bowl winners?' · "
    "'Which positions should we target in free agency?'"
)

if asked and query.strip():
    players: List[PlayerAsset] = load_players()
    with st.spinner("Consulting AI agents..."):
        try:
            system = AgentSystem(players=players, api_key=api_key)
            result = system.ask(query.strip())
        except Exception as exc:
            st.error(f"Error initialising agent system: {exc}")
            st.stop()

    if result["agent"] == "error":
        st.error(result["response"])
    else:
        st.success(f"Answered by: **{result['agent'].title()} Agent**")
        st.markdown(result["response"])
        if result["data_used"]:
            st.caption(
                f"Data used: {', '.join(str(x) for x in result['data_used'][:10])}"
            )
