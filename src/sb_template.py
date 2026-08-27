import logging
from typing import Dict, List

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

POSITION_GROUPS: Dict[str, List[str]] = {
    "QB":      ["QB"],
    "SKILL":   ["WR", "RB", "TE"],
    "OL":      ["OT", "OG", "C"],
    "EDGE":    ["EDGE"],
    "DL":      ["DL"],
    "LB":      ["LB"],
    "DB":      ["CB", "S"],
    "SPECIAL": ["K", "P", "LS"],
}

_POS_TO_GROUP: Dict[str, str] = {
    pos: group
    for group, positions in POSITION_GROUPS.items()
    for pos in positions
}

_AGE_BUCKETS = ["22-25", "26-29", "30+"]

_SB_TEMPLATE = {
    "position_allocation": {
        "QB": 15.0, "SKILL": 25.0, "OL": 15.0, "EDGE": 12.0,
        "DL": 10.0, "LB": 8.0, "DB": 12.0, "SPECIAL": 3.0,
    },
    "age_distribution": {
        "22-25": 38.0, "26-29": 42.0, "30+": 20.0,
    },
    "star_concentration": {
        "top_5": 34.0, "top_10": 54.0,
    },
}


class SuperBowlTemplateAnalyzer:
    """Compares a roster's structure against a Super Bowl winner template."""

    def calculate_position_allocation(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of total cap allocated to each position group.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict mapping position group name to cap percentage (0-100).
        """
        totals: Dict[str, float] = {g: 0.0 for g in POSITION_GROUPS}
        total_cap = 0.0

        for player in roster:
            group = _POS_TO_GROUP.get(player.position.upper().strip())
            if group is None:
                logger.warning(
                    f"Unrecognized position '{player.position}' for {player.name} — skipped"
                )
                continue
            totals[group] += player.cap_hit_2026
            total_cap += player.cap_hit_2026

        if total_cap == 0:
            return {g: 0.0 for g in POSITION_GROUPS}

        return {g: round(v / total_cap * 100, 4) for g, v in totals.items()}

    def calculate_age_distribution(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of roster in each age bucket (22-25, 26-29, 30+).

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict mapping bucket label to percentage of roster count (0-100).
        """
        counts = {b: 0 for b in _AGE_BUCKETS}
        valid = 0

        for player in roster:
            if player.age == 0:
                logger.warning(
                    "Age 0 for %s — excluded from age distribution", player.name
                )
                continue
            valid += 1
            if player.age <= 25:
                counts["22-25"] += 1
            elif player.age <= 29:
                counts["26-29"] += 1
            else:
                counts["30+"] += 1

        if valid == 0:
            return {b: 0.0 for b in _AGE_BUCKETS}

        return {b: round(c / valid * 100, 4) for b, c in counts.items()}

    def calculate_star_concentration(
        self, roster: List[PlayerAsset]
    ) -> Dict[str, float]:
        """Return % of cap held by top 5 and top 10 players by cap hit.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict with keys 'top_5' and 'top_10', each a cap percentage (0-100).
        """
        if not roster:
            return {"top_5": 0.0, "top_10": 0.0}

        sorted_caps = sorted((p.cap_hit_2026 for p in roster), reverse=True)
        total_cap = sum(sorted_caps)
        if total_cap == 0:
            return {"top_5": 0.0, "top_10": 0.0}

        return {
            "top_5":  round(sum(sorted_caps[:5]) / total_cap * 100, 4),
            "top_10": round(sum(sorted_caps[:10]) / total_cap * 100, 4),
        }

    def build_sb_template(self) -> Dict[str, Dict[str, float]]:
        """Return hardcoded SB winner averages (2020-2024).

        Returns:
            Dict with keys: position_allocation, age_distribution, star_concentration.
        """
        return _SB_TEMPLATE

    def calculate_similarity_score(self, roster: List[PlayerAsset]) -> Dict[str, object]:
        """Compare roster metrics against the SB winner template.

        Uses mean absolute percentage deviation per category, capped at 1.0.
        Weights: position 50%, age 30%, concentration 20%.

        Args:
            roster: List of PlayerAsset objects.

        Returns:
            Dict with keys: position_similarity, age_similarity,
            concentration_similarity, overall_similarity (all 0-100), gaps (List[str]).
        """
        template = self.build_sb_template()
        pos_alloc = self.calculate_position_allocation(roster)
        age_dist = self.calculate_age_distribution(roster)
        concentration = self.calculate_star_concentration(roster)

        def _similarity(actual: Dict[str, float], target: Dict[str, float]) -> float:
            deviations = []
            for key in target:
                t = target[key]
                a = actual.get(key, 0.0)
                if t > 0:
                    deviations.append(abs(a - t) / t)
                else:
                    deviations.append(0.0 if a == 0 else 1.0)
            mean_dev = sum(deviations) / len(deviations) if deviations else 0.0
            return round(100.0 * max(0.0, 1.0 - min(mean_dev, 1.0)), 2)

        pos_sim = _similarity(pos_alloc, template["position_allocation"])
        age_sim = _similarity(age_dist, template["age_distribution"])
        con_sim = _similarity(concentration, template["star_concentration"])
        overall = round(0.50 * pos_sim + 0.30 * age_sim + 0.20 * con_sim, 2)

        gaps: List[str] = []
        for group, target_pct in template["position_allocation"].items():
            actual_pct = pos_alloc.get(group, 0.0)
            diff = actual_pct - target_pct
            if abs(diff) >= 1.0:
                direction = "overfunded" if diff > 0 else "underfunded"
                gaps.append(
                    f"{group} {direction} by {abs(diff):.1f}% vs SB template "
                    f"({actual_pct:.1f}% vs {target_pct:.1f}%)"
                )

        return {
            "position_similarity": pos_sim,
            "age_similarity": age_sim,
            "concentration_similarity": con_sim,
            "overall_similarity": overall,
            "gaps": gaps,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.player_valuation import PlayerValuationModel

    demo_roster = [
        PlayerAsset("den_qb_demo", "Demo QB", "QB", "DEN", 27,
                    37_750_000, 4, 20_000_000, 150_000_000, 45.0, 1050, 0),
        PlayerAsset("den_wr_demo", "Demo WR", "WR", "DEN", 25,
                    24_900_000, 3, 15_000_000, 120_000_000, 22.0, 900, 2),
        PlayerAsset("den_ot_demo", "Demo OT", "OT", "DEN", 35,
                    23_750_000, 1, 5_000_000, 30_000_000, 0.0, 1050, 0),
        PlayerAsset("den_edge_demo", "Demo EDGE", "EDGE", "DEN", 28,
                    34_000_000, 5, 25_000_000, 170_000_000, 18.0, 800, 3),
    ]

    model = PlayerValuationModel()
    valued = model.value_roster(demo_roster)
    analyzer = SuperBowlTemplateAnalyzer()

    logger.info("Position allocation: %s", analyzer.calculate_position_allocation(valued))
    logger.info("Age distribution: %s", analyzer.calculate_age_distribution(valued))
    logger.info("Star concentration: %s", analyzer.calculate_star_concentration(valued))
    score = analyzer.calculate_similarity_score(valued)
    logger.info("Similarity: %.1f/100", score['overall_similarity'])
    for gap in score["gaps"]:
        logger.info("  %s", gap)
