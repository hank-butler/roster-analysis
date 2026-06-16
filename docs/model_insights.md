# Roster Valuation Model — Analytical Notes

## How the Model Works

The model treats each player contract like a financial bond:

- **Fair Value** = expected performance value × (1 − risk score)
- **Efficiency Ratio** = expected value / cap hit (>1.0 = good value, <1.0 = overpaid)
- **Sharpe Ratio** = risk-adjusted return (higher = better value per unit of risk)
- **Risk Score** = weighted combination of injury history (40%), age vs. position peak (40%), and positional longevity risk (20%)

EPA (Expected Points Added) is normalised to a per-season average across available seasons, so a 2-season player and a 3-season player are on the same scale.

---

## Key Insights — SF 49ers 2026 Roster

### ✅ Brock Purdy is legitimately undervalued
At ~$23.7M cap hit, the model values him at ~$48M fair value (efficiency ≈ 2.1×). This is economically correct: elite young QBs on cost-controlled contracts routinely create $40–50M+ in market value. Purdy's 2023–24 EPA ranks him among the top QBs in the league.

### ✅ Skill-position depth is good value
Young players on cheap deals (backup OL, developmental DL like Mykel Williams) show efficiency ratios of 1.7–1.9×. The model correctly identifies these as positive-value contract positions.

### ⚠️ Nick Bosa appears overvalued by the model — this is a known limitation
The EPA metric doesn't capture elite pass-rushing value. DL/EDGE players who generate significant pressure and disruption beyond what shows up in scoring EPA will always look "overvalued" under this model. Frame Bosa's score as a cap concentration risk flag, not a performance quality judgement.

### ⚠️ George Kittle is borderline fair/overvalued due to age penalty
At 31 years old (4 years past the model's TE peak age of 27), his risk score is elevated, pushing fair value below his $14.1M cap hit. This is a conservative read — his production remains elite, but the model correctly highlights succession planning risk.

### ⚠️ LB/OL valuations are directional, not precise
Fred Warner ($17.9M) and Trent Williams ($20M) show as overvalued by the model because EPA is a weak signal for linebackers and offensive linemen. Use these scores for relative cap allocation analysis, not absolute player quality judgement.

---

## Model Constraints

| Constraint | Implication |
|---|---|
| EPA only — no PFF, tracking data, or snap grades | Non-skill positions are under-valued by the metric |
| 2023–2024 data only (2025 stats not yet published) | Recent scheme changes or injuries may not be reflected |
| OTC salary-cap page lacks `years_remaining` detail | All players default to 1 year remaining; NPV analysis is approximate |
| ~32% of players lack position data | 2026 FA signings not in historical roster files; assigned positional averages |
| `total_contract_value` is $0 for all players | The OTC salary-cap HTML renders this in a multi-scenario format that doesn't parse cleanly; `cap_hit` and `guaranteed_money` are reliable |

---

## Recommended Use

- **Best for:** Identifying relative value within a position group, cap concentration analysis, draft/FA target prioritisation
- **Not for:** Absolute player quality rankings across positions, DL/OL/LB performance evaluation
- **Strongest signal:** QB and skill-position (WR, TE, RB) comparisons where EPA is a meaningful performance proxy
