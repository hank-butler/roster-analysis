# Roster Valuation Model — Analytical Notes

## How the Model Works

The model treats each player contract like a financial bond:

- **Fair Value** = expected performance value × (1 − risk score)
- **Efficiency Ratio** = expected value / cap hit (>1.0 = good value, <1.0 = overpaid)
- **Sharpe Ratio** = risk-adjusted return (higher = better value per unit of risk)
- **Risk Score** = weighted combination of injury history (40%), age vs. position peak (40%), and positional longevity risk (20%)

EPA (Expected Points Added) is normalised to a per-season average across available seasons, so a 2-season player and a 3-season player are on the same scale.

---

## Key Insights — Denver Broncos 2026 Roster

### ✅ Bo Nix is legitimately undervalued
At a $5.1M cap hit (rookie-scale deal, age 26), the model puts his efficiency ratio at ~11.0×. This is economically correct: a starting-caliber QB producing at this level for rookie-scale money is one of the largest team-building advantages in the league while the deal lasts.

### ✅ Marvin Mims shows strong positive value
At age 24 with a $6.1M cap hit, Mims posts an efficiency ratio of ~3.1× — the second-best value on the roster behind Nix. This is a case where the model's EPA-based skill-position signal is meaningful: a young receiver still on a below-market deal.

### ⚠️ Zach Allen appears overvalued by the model — this is a known limitation
At $16.5M cap hit (age 29), Allen's efficiency ratio comes in at ~0.6×. EPA doesn't capture elite pass-rushing/interior-disruption value, so DL/EDGE players who generate pressure beyond what shows up in scoring EPA will always look "overvalued" under this model. Treat this as a cap-concentration flag, not a performance verdict. (D.J. Jones, another interior DL at $14.6M, shows the same pattern at ~0.7×.)

### ⚠️ Evan Engram is borderline fair/overvalued due to age penalty
At 32 years old (5 years past the model's TE peak age of 27), his risk score is elevated (0.36), pushing fair value below his $14.1M cap hit (efficiency ~0.6×). This is a conservative read — it reflects succession-planning risk in the model, not a current-production judgement.

### ⚠️ LB valuations are directional, not precise — and OL/DB valuations are the least reliable numbers in the model
Alex Singleton ($6.0M, efficiency ~1.4×) and Jonathon Cooper ($5.8M, efficiency ~1.4×) show positive value, while Nik Bonitto ($8.4M) is roughly breakeven (~1.0×) — EPA is a weak signal for off-ball/edge linebacker roles generally, so use these for relative cap allocation, not absolute quality reads.

Separately, every offensive lineman (Mike McGlinchey, Quinn Meinerz, Ben Powers, Garett Bolles) and every player logged under the composite `DB` code (Patrick Surtain II, Talanoa Hufanga, Ja'Quan McMillian) clusters at efficiency ≈ 0.03–0.08 despite cap hits from $5.8M to $23.8M. This isn't a performance signal — `OL` and `DB` are fallback position codes the model uses when a player's specific position (e.g. LT vs. LG, or CB vs. S) isn't available, so these players get generic positional averages rather than position-specific valuation. **Do not use these numbers to compare O-line or DB talent** — they reflect a data-mapping gap, not roster evaluation.

---

## Model Constraints

| Constraint | Implication |
|---|---|
| EPA only — no PFF, tracking data, or snap grades | Non-skill positions are under-valued by the metric |
| 2023–2024 data only (2025 stats not yet published) | Recent scheme changes or injuries may not be reflected |
| OTC salary-cap page lacks `years_remaining` detail | All players default to 1 year remaining; NPV analysis is approximate |
| ~32% of players lack position data | 2026 FA signings/trades not in historical roster files; assigned composite codes (`OL`, `DB`) that fall back to positional averages |
| `total_contract_value` is $0 for all players | The OTC salary-cap HTML renders this in a multi-scenario format that doesn't parse cleanly; `cap_hit` and `guaranteed_money` are reliable |

---

## Recommended Use

- **Best for:** Identifying relative value within a position group, cap concentration analysis, draft/FA target prioritisation
- **Not for:** Absolute player quality rankings across positions, DL/OL/DB/LB performance evaluation
- **Strongest signal:** QB and skill-position (WR, TE, RB) comparisons where EPA is a meaningful performance proxy
