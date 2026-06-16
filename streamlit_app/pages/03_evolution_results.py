import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

import random
from typing import Dict, List

import pandas as pd
import streamlit as st

from src.evolution_engine import RosterConstraints
from src.visualizations import plot_evolution_history

st.title("Roster Evolution Engine")

st.info(
    "The evolution engine uses a genetic algorithm to find the optimal 53-man "
    "roster configuration within hard cap constraints. It evaluates fitness across: "
    "portfolio efficiency (40%), risk (25%), position balance (20%), and "
    "cap utilisation (15%)."
)

random.seed(42)
history: List[Dict] = []
best = 0.30
for gen in range(50):
    best = min(0.75, best + random.uniform(0.005, 0.025))
    avg = best * random.uniform(0.70, 0.90)
    history.append(
        {
            "generation": gen,
            "best_fitness": round(best, 4),
            "avg_fitness": round(avg, 4),
            "diversity": round(random.uniform(0.05, 0.20), 4),
        }
    )

st.subheader("Fitness History")
st.plotly_chart(plot_evolution_history(history), use_container_width=True)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Fitness Function")
    st.code(
        "fitness = (\n"
        "    0.40 * efficiency_score    # portfolio efficiency\n"
        "  + 0.25 * (1 - risk_score)   # inverted risk\n"
        "  + 0.20 * position_balance   # positional requirements\n"
        "  + 0.15 * cap_score          # cap utilisation (90–95% optimal)\n"
        ")\n\n"
        "# Invalid rosters receive fitness = -1000",
        language="python",
    )

with col2:
    st.subheader("Roster Constraints")
    constraints = RosterConstraints()
    rows = []
    for pos, (min_c, max_c) in sorted(constraints.position_limits.items()):
        rows.append({"Position": pos, "Min": min_c, "Max": max_c})
    rows.append(
        {
            "Position": "TOTAL",
            "Min": constraints.min_roster_size,
            "Max": constraints.max_roster_size,
        }
    )
    st.table(pd.DataFrame(rows))

st.caption(
    f"Demo run: 50 generations, population 100. "
    f"Final best fitness: {history[-1]['best_fitness']:.4f}"
)
