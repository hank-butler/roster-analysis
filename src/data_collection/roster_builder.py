"""RosterBuilder: Aggregates nfl_data_py performance stats and fuzzy-merges with OTC contract data."""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

EPA_WEIGHTS = {2025: 0.5, 2024: 0.3, 2023: 0.2}
FUZZY_THRESHOLD = 85
GAMES_PER_SEASON = 17

TEAM_NORMALIZER = {
    "LA": "LAR",
    "OAK": "LV",
}

# Position codes collapsed into coarse groups for cross-source consistency
# checks. Different data sources (OTC scrapes, nfl_data_py rosters) use
# heterogeneous position codes for the same role (e.g. "DB" vs "S"/"CB"),
# so exact-string comparison would produce false conflicts. A fuzzy name
# match is only trusted when its position group agrees with the group
# implied by the full-roster position lookup for that (name, team).
POSITION_GROUPS = {
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    "OL": "OL", "OT": "OL", "OG": "OL", "C": "OL", "G": "OL", "T": "OL",
    "DL": "DL", "DE": "DL", "NT": "DL", "EDGE": "DL", "DT": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "DB": "DB", "CB": "DB", "S": "DB", "SAF": "DB", "NCB": "DB", "FS": "DB", "SS": "DB",
    "K": "K",
    "P": "P",
    "LS": "LS",
}


def _position_group(position: Optional[str]) -> Optional[str]:
    """Map a raw position code to its coarse group, or None if unknown/empty."""
    if position is None:
        return None
    pos = str(position).strip().upper()
    if not pos or pos == "NAN":
        return None
    return POSITION_GROUPS.get(pos)


def _normalize_team(team: str) -> str:
    """Normalize team abbreviation to a standard form."""
    t = str(team).upper().strip()
    return TEAM_NORMALIZER.get(t, t)


def _normalize_name(name: str) -> str:
    """Lowercase, remove name suffixes and punctuation for fuzzy matching."""
    name = str(name).lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    return " ".join(name.split())


class RosterBuilder:
    """Aggregates nfl_data_py performance stats and fuzzy-merges with OTC contract data."""

    def __init__(
        self,
        perf_dir: str = "data/raw/performance",
        contract_dir: str = "data/raw/contracts",
        output_dir: str = "data/processed",
    ):
        self.perf_dir = Path(perf_dir)
        self.contract_dir = Path(contract_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Populated by _aggregate_performance; used in merge() to fill unmatched ages
        self._age_lookup: dict = {}  # (norm_name, norm_team) -> age
        # Name-only fallback, used only when a name is unambiguous league-wide
        self._age_lookup_by_name: dict = {}  # norm_name -> age (max across teams)

    def _aggregate_performance(
        self, stats_df: pd.DataFrame, rosters_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Join stats + roster data and aggregate across seasons per player.

        EPA uses weighted decay (2025: 50%, 2024: 30%, 2023: 20%), prorated
        when a player is missing some seasons. Snaps and games_missed are raw
        3-season sums to preserve the valuation model's denominator assumptions.

        Args:
            stats_df: From nfl_data_py.import_seasonal_data — player_id, season,
                      games, passing_epa, rushing_epa, receiving_epa, offense_snaps
                      (no player_name or team).
            rosters_df: From nfl_data_py.import_seasonal_rosters — player_id, season,
                        player_name, position, team.

        Returns:
            DataFrame with one row per player: player_name, team, position,
            epa_total, snaps_played, games_missed.
        """
        # Join stats to rosters to get player_name, position, team
        roster_cols = ["player_id", "season", "player_name", "position", "team"]
        if "birth_date" in rosters_df.columns:
            roster_cols.append("birth_date")
        rosters_slim = rosters_df[roster_cols].drop_duplicates(subset=["player_id", "season"])

        df = stats_df.merge(rosters_slim, on=["player_id", "season"], how="inner")
        if df.empty:
            raise ValueError(
                "Performance/roster join produced 0 rows. Verify that player_id and season "
                "columns exist in both inputs and cover overlapping seasons."
            )
        df["team"] = df["team"].apply(_normalize_team)

        # Compute player age from birth_date (reference year = 2026 for cap analysis)
        if "birth_date" in df.columns:
            current_year = 2026
            df["birth_year"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.year
            df["computed_age"] = current_year - df["birth_year"]

        # Build a broader age lookup from ALL roster rows (covers players who won't
        # match via stats join but whose ages appear in the rosters CSV).
        if "birth_date" in rosters_df.columns:
            current_year = 2026
            full_ages = rosters_df[["player_name", "team", "birth_date"]].copy()
            full_ages["team"] = full_ages["team"].apply(_normalize_team)
            full_ages["birth_year"] = pd.to_datetime(
                full_ages["birth_date"], errors="coerce"
            ).dt.year
            full_ages["computed_age"] = current_year - full_ages["birth_year"]
            full_ages = full_ages.dropna(subset=["computed_age"])
            full_ages["_norm_name"] = full_ages["player_name"].apply(_normalize_name)
            full_ages["_norm_team"] = full_ages["team"].apply(_normalize_team)
            # Keep most recent (highest) age per (name, team)
            self._age_lookup = (
                full_ages.groupby(["_norm_name", "_norm_team"])["computed_age"]
                .max()
                .astype(int)
                .to_dict()
            )
            logger.info(f"Built age lookup with {len(self._age_lookup)} entries from rosters data")

            # Name-only fallback (used when (name, team) misses, e.g. a player
            # who changed teams between the 2023-2025 rosters snapshot and the
            # 2026 OTC contract page). Age ambiguity across same-named players
            # is low-stakes, so simply take the max computed age for the name.
            self._age_lookup_by_name = (
                full_ages.groupby("_norm_name")["computed_age"].max().astype(int).to_dict()
            )
            logger.info(
                f"Built name-only age fallback with {len(self._age_lookup_by_name)} entries"
            )

        # Total EPA per player-season
        epa_cols = [c for c in ["passing_epa", "rushing_epa", "receiving_epa"]
                    if c in df.columns]
        if epa_cols:
            df["season_epa"] = df[epa_cols].fillna(0).sum(axis=1)
        else:
            df["season_epa"] = 0.0

        # Snaps per player-season
        snap_cols = [c for c in ["offense_snaps", "defense_snaps"] if c in df.columns]
        if snap_cols:
            df["season_snaps"] = df[snap_cols].fillna(0).sum(axis=1)
        else:
            df["season_snaps"] = df.get("games", pd.Series(0, index=df.index)).fillna(0) * 65
            logger.warning("No snap columns found — using games * 65 as proxy")

        df["season_games_missed"] = (GAMES_PER_SEASON - df["games"].fillna(0)).clip(lower=0)

        records = []
        for (player_name, team, position), group in df.groupby(
            ["player_name", "team", "position"]
        ):
            available_weights = {
                yr: w for yr, w in EPA_WEIGHTS.items() if yr in group["season"].values
            }
            total_weight = sum(available_weights.values())
            seasons_count = max(len(available_weights), 1)
            if total_weight == 0:
                epa_total = 0.0
            else:
                epa_total = sum(
                    group.loc[group["season"] == yr, "season_epa"].sum() * (w / total_weight)
                    for yr, w in available_weights.items()
                )
            # Normalise to per-season average so epa_total is on a consistent scale
            # regardless of how many seasons of data a player has.
            epa_per_season = epa_total / seasons_count

            age = (
                int(group["computed_age"].max())
                if "computed_age" in group.columns and group["computed_age"].notna().any()
                else 0
            )

            records.append({
                "player_name": player_name,
                "team": team,
                "position": position,
                "age": age,
                "epa_total": round(epa_per_season, 4),
                # Normalise to per-season so snap_factor and injury_risk
                # formulas in PlayerValuationModel work on a single-season scale.
                "snaps_played": int(group["season_snaps"].sum() / seasons_count),
                "games_missed": int(group["season_games_missed"].sum() / seasons_count),
            })

        return pd.DataFrame(records)

    def load_performance_data(self) -> pd.DataFrame:
        """Load and aggregate performance data from Stage 1 CSVs.

        Returns:
            Aggregated per-player DataFrame with epa_total, snaps_played, games_missed.

        Raises:
            FileNotFoundError: If Stage 1 CSVs are missing.
        """
        stats_path = self.perf_dir / "player_stats_2023_2025.csv"
        rosters_path = self.perf_dir / "rosters_2023_2025.csv"
        for p in (stats_path, rosters_path):
            if not p.exists():
                raise FileNotFoundError(
                    f"{p} not found. Run Stage 1 first: "
                    "python collect_all_data.py --force-stage performance"
                )
        stats_df = pd.read_csv(stats_path)
        rosters_df = pd.read_csv(rosters_path)
        logger.info(f"Loaded {len(stats_df)} stat rows and {len(rosters_df)} roster rows")
        return self._aggregate_performance(stats_df, rosters_df)

    def load_contract_data(self, teams: List[str]) -> pd.DataFrame:
        """Load OTC contract CSVs for the given team abbreviations.

        Args:
            teams: List of team abbreviations (e.g., ['DEN', 'LAC']).

        Returns:
            Combined contract DataFrame.

        Raises:
            FileNotFoundError: If no contract CSVs are found.
        """
        frames = []
        sb_teams = {"KC", "TB", "PHI"}
        for team in teams:
            if team in sb_teams:
                path = self.contract_dir / "sb_winners" / f"{team.lower()}_2026.csv"
            else:
                path = self.contract_dir / f"{team.lower()}_2026.csv"
            if not path.exists():
                logger.warning(f"[{team}] Contract file not found: {path}. Skipping.")
                continue
            frames.append(pd.read_csv(path))

        if not frames:
            raise FileNotFoundError(
                "No contract CSVs found. Run Stage 2 first: "
                "python collect_all_data.py --force-stage contracts"
            )
        combined = pd.concat(frames, ignore_index=True)
        combined = combined[
            combined["player_name"].astype(str).str.strip() != "Top 51 Cutoff"
        ].reset_index(drop=True)
        return combined

    def _build_position_lookup(self) -> Tuple[Dict[Tuple[str, str], str], Dict[str, str]]:
        """Build position lookups from full roster data.

        The roster CSV from nfl_data_py contains ALL players (including OL, DL, LB,
        S, CB, K, P) with their positions — unlike the stats join which only covers
        skill positions with EPA data.

        Returns:
            Tuple of (team_lookup, name_only_lookup):
              - team_lookup: (normalized_name, normalized_team) → uppercase position.
              - name_only_lookup: normalized_name → uppercase position, populated
                ONLY for names that map to a single position league-wide (used as
                a fallback for players who changed teams since the rosters
                snapshot, e.g. a name found on rosters under a different team
                than the OTC contract lists).
        """
        rosters_path = self.perf_dir / "rosters_2023_2025.csv"
        if not rosters_path.exists():
            logger.warning(f"Roster file not found for position lookup: {rosters_path}")
            return {}, {}
        rosters_df = pd.read_csv(rosters_path, usecols=["player_name", "team", "position"])
        lookup: dict = {}
        name_positions: dict = {}  # norm_name -> set of positions seen league-wide
        for _, row in rosters_df.iterrows():
            pos = str(row.get("position", "")).strip()
            if pos and pos.upper() != "NAN":
                pos = pos.upper()
                norm_name = _normalize_name(str(row["player_name"]))
                key = (norm_name, _normalize_team(str(row["team"])))
                # Prefer the most recent / non-empty entry; last-write wins
                lookup[key] = pos
                name_positions.setdefault(norm_name, set()).add(pos)
        # Keep only names that resolve to exactly one position league-wide;
        # drop ambiguous names (e.g. same name, different players/positions).
        name_only_lookup = {
            name: next(iter(positions))
            for name, positions in name_positions.items()
            if len(positions) == 1
        }
        logger.info(f"Built position lookup with {len(lookup)} entries from rosters data")
        logger.info(
            f"Built name-only position fallback with {len(name_only_lookup)} unambiguous entries"
        )
        return lookup, name_only_lookup

    def merge(
        self,
        perf_df: pd.DataFrame,
        contract_df: pd.DataFrame,
        unmatched_filename: str = "unmatched_players.csv",
    ) -> pd.DataFrame:
        """Fuzzy-merge performance stats onto OTC contract rows.

        Matches on normalized player name + team (not position, since OTC data
        lacks reliable position info). Matched rows get performance columns
        populated; unmatched rows remain with NaN performance fields and are
        logged to `unmatched_filename` under output_dir.

        Args:
            perf_df: Output of _aggregate_performance().
            contract_df: Loaded OTC contract DataFrame.
            unmatched_filename: Filename (under output_dir) to write unmatched
                rows to. Distinct callers (e.g. build_afc_west vs
                build_sb_winners) should pass distinct filenames so their
                unmatched logs don't clobber each other.

        Returns:
            Merged DataFrame with one row per OTC player.
        """
        perf = perf_df.copy()
        contracts = contract_df.copy()

        perf["_norm_name"] = perf["player_name"].apply(_normalize_name)
        perf["_norm_team"] = perf["team"].apply(_normalize_team)
        contracts["_norm_name"] = contracts["player_name"].apply(_normalize_name)
        contracts["_norm_team"] = contracts["team"].apply(_normalize_team)

        base_perf_cols = ["epa_total", "snaps_played", "games_missed"]
        # Also copy computed age from nfl_data_py when available
        perf_cols = base_perf_cols + (["age"] if "age" in perf.columns else [])
        matched_rows = []
        unmatched_rows = []

        # Position lookup covers ALL roster players (OL, DL, LB, S, CB, K, P)
        # whereas perf_df only has skill-position players with EPA data.
        pos_lookup, pos_lookup_by_name = self._build_position_lookup()

        for _, otc_row in contracts.iterrows():
            otc_name = otc_row["_norm_name"]
            otc_team = otc_row["_norm_team"]

            # Match on team only (position unreliable from OTC)
            candidates = perf[perf["_norm_team"] == otc_team]

            best_score, best_match = 0, None
            for _, perf_row in candidates.iterrows():
                score = fuzz.token_sort_ratio(otc_name, perf_row["_norm_name"])
                if score > best_score:
                    best_score, best_match = score, perf_row

            row_dict = otc_row.drop(labels=["_norm_name", "_norm_team"]).to_dict()

            accept_match = best_match is not None and best_score >= FUZZY_THRESHOLD
            if accept_match:
                lookup_group = _position_group(pos_lookup.get((otc_name, otc_team)))
                match_group = _position_group(best_match.get("position"))
                if lookup_group is not None and match_group is not None and lookup_group != match_group:
                    logger.warning(
                        f"Rejected fuzzy match: OTC '{otc_row['player_name']}' ({otc_team}, "
                        f"lookup position group={lookup_group}) vs perf '{best_match['player_name']}' "
                        f"({match_group}) — score={best_score}, position groups conflict"
                    )
                    accept_match = False

            if accept_match:
                for col in perf_cols:
                    row_dict[col] = best_match[col]
                # Backfill position from nfl_data_py perf match if OTC position is null
                if pd.isna(row_dict.get("position")) or str(row_dict.get("position", "")).strip() == "":
                    row_dict["position"] = best_match.get("position", "")
                # If still empty, fall back to full-roster position lookup
                # (name+team first, then name-only for players whose team on
                # the OTC page differs from the rosters snapshot).
                if pd.isna(row_dict.get("position")) or str(row_dict.get("position", "")).strip() == "":
                    row_dict["position"] = pos_lookup.get(
                        (otc_name, otc_team), pos_lookup_by_name.get(otc_name, "")
                    )
            else:
                for col in base_perf_cols:
                    row_dict[col] = np.nan
                # Try to fill age from broader roster lookup even without a perf match
                looked_up_age = self._age_lookup.get((otc_name, otc_team))
                if looked_up_age is None:
                    looked_up_age = self._age_lookup_by_name.get(otc_name)
                if looked_up_age is not None:
                    row_dict["age"] = looked_up_age
                # Backfill position from full roster data for unmatched players
                # (name+team first, then name-only fallback).
                if pd.isna(row_dict.get("position")) or str(row_dict.get("position", "")).strip() == "":
                    row_dict["position"] = pos_lookup.get(
                        (otc_name, otc_team), pos_lookup_by_name.get(otc_name, "")
                    )
                has_suggestion = best_match is not None and best_score >= 60
                unmatched_rows.append({
                    "otc_name": otc_row["player_name"],
                    "otc_team": otc_row.get("team", ""),
                    "otc_position": otc_row.get("position", ""),
                    "nfl_name": best_match["player_name"] if has_suggestion else "",
                    "nfl_team": best_match["team"] if has_suggestion else "",
                    "nfl_position": best_match["position"] if has_suggestion else "",
                    "match_score": best_score if has_suggestion else 0,
                })

            matched_rows.append(row_dict)

        merged_df = pd.DataFrame(matched_rows)

        total = len(contracts)
        matched_count = total - len(unmatched_rows)
        match_pct = matched_count / total * 100 if total > 0 else 0
        logger.info(f"Fuzzy match rate: {matched_count}/{total} ({match_pct:.1f}%)")
        if match_pct < 50:
            logger.warning(
                f"Match rate below 50% — check team normalization and name formats. "
                f"Top unmatched scores: {sorted([r['match_score'] for r in unmatched_rows], reverse=True)[:5]}"
            )

        unmatched_path = self.output_dir / unmatched_filename
        unmatched_frame = pd.DataFrame(
            unmatched_rows if unmatched_rows else [],
            columns=["otc_name", "otc_team", "otc_position",
                     "nfl_name", "nfl_team", "nfl_position", "match_score"],
        )
        unmatched_frame.to_csv(unmatched_path, index=False)
        if unmatched_rows:
            logger.info(f"{len(unmatched_rows)} unmatched players → {unmatched_path}")

        return merged_df.drop(columns=["_norm_name", "_norm_team"], errors="ignore")

    def build_afc_west(self) -> pd.DataFrame:
        """Build and save afc_west_rosters.csv.

        Returns:
            Merged DataFrame for DEN, KC, LAC, LV.
        """
        output_path = self.output_dir / "afc_west_rosters.csv"
        if output_path.exists():
            logger.info(f"[SKIP] {output_path} already exists")
            return pd.read_csv(output_path)
        perf = self.load_performance_data()
        contracts = self.load_contract_data(["DEN", "KC", "LAC", "LV"])
        merged = self.merge(perf, contracts)
        merged.to_csv(output_path, index=False)
        logger.info(f"Saved AFC West roster ({len(merged)} players) to {output_path}")
        return merged

    def build_sb_winners(self) -> pd.DataFrame:
        """Build and save sb_winners_combined.csv.

        Returns:
            Merged DataFrame for KC, TB, PHI.
        """
        output_path = self.output_dir / "sb_winners_combined.csv"
        if output_path.exists():
            logger.info(f"[SKIP] {output_path} already exists")
            return pd.read_csv(output_path)
        perf = self.load_performance_data()
        contracts = self.load_contract_data(["KC", "TB", "PHI"])
        merged = self.merge(perf, contracts, unmatched_filename="unmatched_sb_winners.csv")
        merged.to_csv(output_path, index=False)
        logger.info(f"Saved SB winners roster ({len(merged)} players) to {output_path}")
        return merged
