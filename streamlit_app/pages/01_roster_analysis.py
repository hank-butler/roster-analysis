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

MIN_CAP_THRESHOLD = 5_000_000  # exclude minimum-deal depth players from valuation tables

KNOWN_POSITIONS = {
    "QB", "WR", "RB", "TE", "OT", "OG", "C",
    "EDGE", "DL", "LB", "CB", "S", "K", "P", "LS",
}

def _filter_table(df):
    """Keep only players with meaningful cap hits and NFL-standard positions.

    Excludes players with composite/non-standard position codes (e.g. 'DB', 'OL')
    that fall back to model defaults and produce unreliable valuations.
    """
    return df[
        (df["cap_hit"] >= MIN_CAP_THRESHOLD) &
        (df["position"].isin(KNOWN_POSITIONS))
    ]

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Most Overvalued")
    ov = _filter_table(pa.identify_overvalued()).head(5)
    if ov.empty:
        st.success("No significantly overvalued players")
    else:
        st.dataframe(
            ov[["name", "position", "cap_hit", "fair_value", "efficiency_ratio", "pct_overvalued"]],
            use_container_width=True,
            hide_index=True,
        )

with col_right:
    st.subheader("Most Undervalued")
    uv = _filter_table(pa.identify_undervalued()).head(5)
    if uv.empty:
        st.success("No significantly undervalued players")
    else:
        st.dataframe(
            uv[["name", "position", "cap_hit", "fair_value", "efficiency_ratio", "pct_undervalued"]],
            use_container_width=True,
            hide_index=True,
        )

st.divider()

with st.expander("📋 Model Notes & Known Limitations"):
    st.markdown("""
**How to read these numbers:**
- **Efficiency > 1.0** = player creates more value than their cap hit — good contract
- **Efficiency < 1.0** = cap hit exceeds modelled value — watch for over-commitment

**Key insights on the 2026 SF roster:**
- **Brock Purdy (efficiency ~2.1×)** — legitimately undervalued on a cost-controlled deal. Elite QBs command $40–50M+ on the open market; his $23.7M cap hit is well below that
- **Nick Bosa (efficiency ~0.4×)** — the EPA metric does not capture elite pass-rushing value. DL/EDGE players who generate pressure and disruption show as overvalued under any EPA-based model. Treat this as a cap-concentration flag, not a performance verdict
- **George Kittle (borderline)** — the age penalty (31, four years past TE peak) reduces his modelled fair value. Reflects succession-planning risk, not current performance
- **LB/OL valuations are directional** — Fred Warner and Trent Williams use positional EPA averages, which are a weak signal for their roles

**Model constraints:** EPA only (no PFF grades or tracking data); 2023–2024 seasons (2025 stats not yet published); all contracts default to 1 year remaining. Tables above exclude players earning below $5M — backup/minimum-deal players receive synthetic positional-average EPA and would otherwise dominate the undervalued list due to the position premium in the baseline.
    """)
    st.caption("Full notes: docs/model_insights.md")
