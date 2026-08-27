import logging
from typing import Dict, List

import plotly.graph_objects as go

from src.player_valuation import PlayerAsset, PortfolioAnalyzer
from src.sb_template import POSITION_GROUPS, SuperBowlTemplateAnalyzer

logger = logging.getLogger(__name__)

TEAM_COLORS = {
    "DEN": "#FB4F14",
    "KC":  "#E31837",
    "LAC": "#0080C6",
    "LV":  "#000000",
}
_DEFAULT_COLOR = "#888888"


def _team_color(team: str) -> str:
    return TEAM_COLORS.get(team.upper(), _DEFAULT_COLOR)


def plot_roster_efficiency_scatter(
    teams_data: Dict[str, List[PlayerAsset]],
) -> go.Figure:
    """Scatter plot of portfolio risk vs efficiency, one point per team.

    Includes a shaded 'SB Winner Zone' (risk < 0.25, efficiency > 1.15).

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    fig.add_shape(
        type="rect",
        x0=0, x1=0.25, y0=1.15, y1=2.0,
        fillcolor="rgba(255, 215, 0, 0.15)",
        line=dict(color="gold", dash="dash"),
        layer="below",
    )
    fig.add_annotation(
        x=0.125, y=1.9, text="SB Winner Zone",
        showarrow=False, font=dict(color="goldenrod", size=11),
    )

    for team, roster in teams_data.items():
        if not roster:
            continue
        analyzer = PortfolioAnalyzer(roster)
        fig.add_trace(go.Scatter(
            x=[analyzer.portfolio_risk()],
            y=[analyzer.portfolio_efficiency()],
            mode="markers+text",
            marker=dict(size=14, color=_team_color(team)),
            text=[team],
            textposition="top center",
            name=team,
        ))

    fig.update_layout(
        title="AFC West — Portfolio Risk vs Efficiency",
        xaxis_title="Portfolio Risk (lower = better)",
        yaxis_title="Portfolio Efficiency (value / cost)",
        showlegend=False,
    )
    return fig


def plot_position_allocation_comparison(
    teams_data: Dict[str, List[PlayerAsset]],
    sb_template: Dict,
) -> go.Figure:
    """Grouped bar chart of position group cap allocation across teams + SB template.

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.
        sb_template: Output of SuperBowlTemplateAnalyzer.build_sb_template().

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()
    analyzer = SuperBowlTemplateAnalyzer()
    groups = list(POSITION_GROUPS.keys())

    for team, roster in teams_data.items():
        alloc = analyzer.calculate_position_allocation(roster)
        fig.add_trace(go.Bar(
            name=team,
            x=groups,
            y=[alloc.get(g, 0) for g in groups],
            marker_color=_team_color(team),
        ))

    template_alloc = sb_template["position_allocation"]
    fig.add_trace(go.Bar(
        name="SB Template",
        x=groups,
        y=[template_alloc.get(g, 0) for g in groups],
        marker_color="rgba(255, 215, 0, 0.7)",
        marker_line=dict(color="goldenrod", width=1.5),
    ))

    fig.update_layout(
        barmode="group",
        title="Cap Allocation by Position Group vs SB Template",
        xaxis_title="Position Group",
        yaxis_title="% of Cap",
    )
    return fig


def plot_evolution_history(history: List[Dict]) -> go.Figure:
    """Dual line chart of best and avg fitness over evolution generations.

    Annotates the generation where best_fitness first reaches its maximum.

    Args:
        history: List of dicts with keys generation, best_fitness, avg_fitness.
            This is the history list returned by EvolutionEngine.evolve().

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if not history:
        fig.update_layout(title="Evolution History (no data)")
        return fig

    gens = [h["generation"] for h in history]
    best = [h["best_fitness"] for h in history]
    avg = [h["avg_fitness"] for h in history]

    fig.add_trace(go.Scatter(x=gens, y=best, mode="lines", name="Best Fitness",
                             line=dict(color="#AA0000", width=2)))
    fig.add_trace(go.Scatter(x=gens, y=avg, mode="lines", name="Avg Fitness",
                             line=dict(color="#666666", dash="dot")))

    peak_idx = best.index(max(best))
    fig.add_annotation(
        x=gens[peak_idx], y=best[peak_idx],
        text=f"Peak gen {gens[peak_idx]}",
        showarrow=True, arrowhead=2,
    )

    fig.update_layout(
        title="Evolution Fitness History",
        xaxis_title="Generation",
        yaxis_title="Fitness Score",
    )
    return fig


def plot_player_value_scatter(
    players: List[PlayerAsset],
    highlight_team: str = "DEN",
) -> go.Figure:
    """Scatter of cap_hit_2026 vs expected_value, colored by over/under-valued.

    Green = undervalued (value > cap * 1.15), red = overvalued (cap > value * 1.15),
    grey = fair value. Marker size inversely proportional to risk_score.
    Labels the top 3 most over- and undervalued players.

    Args:
        players: List of valued PlayerAsset objects.
        highlight_team: Team abbreviation used in the chart title.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if not players:
        fig.update_layout(title="Player Value vs Cap Hit")
        return fig

    max_cap = max((p.cap_hit_2026 for p in players), default=1)

    fig.add_trace(go.Scatter(
        x=[0, max_cap * 1.1],
        y=[0, max_cap * 1.1],
        mode="lines",
        name="Fair Value",
        line=dict(color="grey", dash="dash"),
        showlegend=False,
    ))

    overvalued = sorted(
        [p for p in players
         if p.cap_hit_2026 > p.expected_value * 1.15 and p.expected_value > 0],
        key=lambda p: p.cap_hit_2026 - p.expected_value, reverse=True
    )[:3]
    undervalued = sorted(
        [p for p in players if p.expected_value > p.cap_hit_2026 * 1.15],
        key=lambda p: p.expected_value - p.cap_hit_2026, reverse=True
    )[:3]
    label_ids = {p.player_id for p in overvalued + undervalued}

    for player in players:
        if player.cap_hit_2026 <= 0 or player.expected_value <= 0:
            continue
        if player.cap_hit_2026 > player.expected_value * 1.15:
            color = "red"
        elif player.expected_value > player.cap_hit_2026 * 1.15:
            color = "green"
        else:
            color = "grey"

        size = max(6, 20 * (1 - player.risk_score))
        label = player.name if player.player_id in label_ids else ""

        fig.add_trace(go.Scatter(
            x=[player.cap_hit_2026],
            y=[player.expected_value],
            mode="markers+text" if label else "markers",
            marker=dict(size=size, color=color, opacity=0.7),
            text=label,
            textposition="top center",
            name=player.name,
            showlegend=False,
        ))

    fig.update_layout(
        title=f"{highlight_team} — Player Value vs Cap Hit",
        xaxis_title="Cap Hit 2026 ($)",
        yaxis_title="Expected Value ($)",
    )
    return fig


def plot_sb_similarity_radar(
    teams_data: Dict[str, List[PlayerAsset]],
    sb_template: Dict,
) -> go.Figure:
    """Radar chart comparing teams to the SB template on 5 structural axes.

    Axes: QB spend %, Skill spend %, OL spend %, Age 26-29 %, Top-5 cap concentration %.

    Args:
        teams_data: Dict mapping team abbreviation to their valued roster.
        sb_template: Output of SuperBowlTemplateAnalyzer.build_sb_template().

    Returns:
        Plotly Figure.
    """
    axes = ["QB spend", "Skill spend", "OL spend", "Age 26-29", "Top-5 cap"]
    fig = go.Figure()
    analyzer = SuperBowlTemplateAnalyzer()

    def _radar_values(roster: List[PlayerAsset]) -> List[float]:
        alloc = analyzer.calculate_position_allocation(roster)
        age = analyzer.calculate_age_distribution(roster)
        conc = analyzer.calculate_star_concentration(roster)
        return [
            alloc.get("QB", 0),
            alloc.get("SKILL", 0),
            alloc.get("OL", 0),
            age.get("26-29", 0),
            conc.get("top_5", 0),
        ]

    for team, roster in teams_data.items():
        if not roster:
            continue
        vals = _radar_values(roster)
        color = _team_color(team)
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name=team,
            line=dict(color=color),
        ))

    template_vals = [
        sb_template["position_allocation"].get("QB", 0),
        sb_template["position_allocation"].get("SKILL", 0),
        sb_template["position_allocation"].get("OL", 0),
        sb_template["age_distribution"].get("26-29", 0),
        sb_template["star_concentration"].get("top_5", 0),
    ]
    fig.add_trace(go.Scatterpolar(
        r=template_vals + [template_vals[0]],
        theta=axes + [axes[0]],
        fill="toself",
        name="SB Template",
        line=dict(color="goldenrod", dash="dash"),
    ))

    fig.update_layout(
        title="SB Template Similarity Radar",
        polar=dict(radialaxis=dict(visible=True, range=[0, 50])),
    )
    return fig


def plot_age_distribution(roster: List[PlayerAsset]) -> go.Figure:
    """Grouped bar chart comparing roster age distribution to the SB template.

    Args:
        roster: List of PlayerAsset objects.

    Returns:
        Plotly Figure.
    """
    analyzer = SuperBowlTemplateAnalyzer()
    buckets = ["22-25", "26-29", "30+"]
    roster_dist = analyzer.calculate_age_distribution(roster)
    template_dist = analyzer.build_sb_template()["age_distribution"]

    fig = go.Figure([
        go.Bar(
            name="Current Roster",
            x=buckets,
            y=[roster_dist.get(b, 0) for b in buckets],
            marker_color="#AA0000",
        ),
        go.Bar(
            name="SB Template",
            x=buckets,
            y=[template_dist.get(b, 0) for b in buckets],
            marker_color="rgba(255, 215, 0, 0.7)",
            marker_line=dict(color="goldenrod", width=1.5),
        ),
    ])

    fig.update_layout(
        barmode="group",
        title="Age Distribution vs SB Template",
        xaxis_title="Age Bucket",
        yaxis_title="% of Roster",
    )
    return fig


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    from src.player_valuation import PlayerValuationModel

    model = PlayerValuationModel()
    demo_players = [
        PlayerAsset("den_qb_d", "Nix", "QB", "DEN", 27,
                    37_000_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("den_wr_d", "Sutton", "WR", "DEN", 26,
                    24_000_000, 3, 12_000_000, 96_000_000, 22.0, 900, 2),
        PlayerAsset("kc_qb_d", "Mahomes", "QB", "KC", 33,
                    20_000_000, 1, 10_000_000, 20_000_000, 15.0, 900, 2),
    ]
    valued = model.value_roster(demo_players)
    teams = {
        "DEN": [p for p in valued if p.team == "DEN"],
        "KC":  [p for p in valued if p.team == "KC"],
    }
    template = SuperBowlTemplateAnalyzer().build_sb_template()

    fig = plot_roster_efficiency_scatter(teams)
    logger.info("Efficiency scatter: %d traces", len(fig.data))
    fig2 = plot_age_distribution(teams["DEN"])
    logger.info("Age distribution: %d traces", len(fig2.data))
