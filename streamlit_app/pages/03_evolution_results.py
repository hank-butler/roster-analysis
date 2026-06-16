import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

import json

import pandas as pd
import streamlit as st

from src.evolution_engine import RosterConstraints
from src.visualizations import plot_evolution_history

RESULTS_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "evolution_results.json"

st.title("Roster Evolution Engine")

st.markdown(
    """
    The evolution engine applies a **genetic algorithm** to find an optimal roster configuration
    within hard cap constraints. Starting from the current SF 49ers roster, it explores thousands
    of roster variations — swapping players in and out, crossing over configurations, and
    mutating selections — to maximise a multi-objective fitness function.

    > *Analysis covers positions where we have performance data: QB · WR · RB · TE · DL · LB · K · P · LS*
    """
)

# ---- Load real results ---------------------------------------------------

if not RESULTS_PATH.exists():
    st.error(
        f"Evolution results not found at {RESULTS_PATH}. "
        "Run: `python scripts/run_evolution.py`"
    )
    st.stop()

with open(RESULTS_PATH) as f:
    results = json.load(f)

current = results["current_roster"]
evolved = results["evolved_roster"]
changes = results["changes"]
history = results["history"]
meta = results["metadata"]

# ---- Fitness function explanation ----------------------------------------

with st.expander("⚙️ How the fitness function works"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.code(
            "fitness = (\n"
            "    0.40 × efficiency_score    # value per cap dollar\n"
            "  + 0.25 × (1 − risk_score)   # lower risk = better\n"
            "  + 0.20 × position_balance   # meets NFL roster rules\n"
            "  + 0.15 × cap_utilisation    # 90–95% cap = optimal\n"
            ")\n\n"
            "# Invalid rosters receive fitness = −1000",
            language="python",
        )
    with col_b:
        constraints = RosterConstraints()
        pos_rows = [
            {"Position": pos, "Min": mn, "Max": mx}
            for pos, (mn, mx) in sorted(constraints.position_limits.items())
        ]
        st.caption("Full 53-man constraints (standard NFL rules)")
        st.dataframe(pd.DataFrame(pos_rows), hide_index=True, use_container_width=True)

st.divider()

# ---- Before vs After summary ---------------------------------------------

st.subheader("Current SF Roster vs Evolved Optimal Roster")
st.caption(
    f"Evolution run: {meta['population_size']} population · {len(history)} generations · "
    f"${meta['salary_cap']/1e6:.0f}M cap (skill + DL/LB portion)"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Best Fitness Achieved",
    f"{evolved['fitness']:.4f}",
    help="0 = worst possible, 1 = theoretical perfect",
)
col2.metric(
    "Portfolio Efficiency",
    f"{evolved['portfolio_efficiency']:.2f}×",
    delta=f"{evolved['portfolio_efficiency'] - current['portfolio_efficiency']:+.2f}×",
)
col3.metric(
    "Portfolio Risk",
    f"{evolved['portfolio_risk']:.3f}",
    delta=f"{evolved['portfolio_risk'] - current['portfolio_risk']:+.3f}",
    delta_color="inverse",
)
col4.metric(
    "Cap Used",
    f"${evolved['cap_used']/1e6:.1f}M",
    delta=f"${(evolved['cap_used'] - current['cap_used'])/1e6:+.1f}M",
    delta_color="inverse",
)

st.divider()

# ---- Fitness history chart -----------------------------------------------

st.subheader("Fitness Progression Across Generations")
st.plotly_chart(plot_evolution_history(history), use_container_width=True)

st.divider()

# ---- Roster changes ------------------------------------------------------

st.subheader("What the Algorithm Changed")

col_add, col_rem = st.columns(2)

with col_add:
    st.markdown(f"**✅ Players Added** ({len(changes['added'])} players brought in)")
    if changes["added"]:
        add_df = pd.DataFrame([
            {
                "Name": p["name"],
                "Pos": p["position"],
                "Team": p["team"],
                "Cap Hit": f"${p['cap_hit']/1e6:.1f}M",
                "Efficiency": f"{p['efficiency_ratio']:.2f}×",
            }
            for p in changes["added"]
        ])
        st.dataframe(add_df, hide_index=True, use_container_width=True)

with col_rem:
    st.markdown(f"**🔴 Players Released** ({len(changes['removed'])} players phased out)")
    if changes["removed"]:
        rem_df = pd.DataFrame([
            {
                "Name": p["name"],
                "Pos": p["position"],
                "Team": p["team"],
                "Cap Hit": f"${p['cap_hit']/1e6:.1f}M",
                "Efficiency": f"{p['efficiency_ratio']:.2f}×",
            }
            for p in changes["removed"]
        ])
        st.dataframe(rem_df, hide_index=True, use_container_width=True)

st.caption(
    f"{changes['kept_count']} players retained from the current SF roster. "
    f"Additions drawn from all {len(set(p['team'] for p in changes['added']))} NFC West teams."
)

st.divider()

# ---- Evolved roster full view --------------------------------------------

with st.expander("📋 View full evolved roster"):
    evolved_df = pd.DataFrame([
        {
            "Name": p["name"],
            "Pos": p["position"],
            "Team": p["team"],
            "Age": p["age"],
            "Cap Hit": f"${p['cap_hit']/1e6:.1f}M",
            "Fair Value": f"${p['fair_value']/1e6:.1f}M",
            "Efficiency": f"{p['efficiency_ratio']:.2f}×",
            "Risk": f"{p['risk_score']:.2f}",
        }
        for p in evolved["players"]
    ])
    st.dataframe(evolved_df, hide_index=True, use_container_width=True)
