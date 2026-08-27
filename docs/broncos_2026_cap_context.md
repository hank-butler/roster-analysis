# Denver Broncos — 2026 Cap Context (Research Notes)

Research date: 2026-08-27. NFL cap figures move throughout the year as
teams make moves; figures below are dated where the source indicates a
snapshot in time.

## Cap Space

- **Total 2026 cap space available: $37,317,460**
  Source: [Over The Cap — Denver Broncos Salary Cap](https://overthecap.com/salary-cap/denver-broncos)
  (live page, fetched 2026-08-27).
- **Total cap allocated (Top 51): $262,687,367**
  Source: same OTC page as above.
- Note on discrepancy: an earlier SI.com (OnSI network) article dated
  March 31, 2026 cited the Broncos at roughly **$18.8M** in cap space at
  that point in the offseason, and a separately-surfaced search snippet
  (undated, could not confirm publish date) cited **$29,487,632**.
  Cap space is a moving target — it rises through the year as the league
  cap number gets finalized, post-June-1 designations resolve, and
  performance/incentive escalators clear. The $37.3M figure from the live
  OTC page is treated as authoritative for this project since it is the
  most current, directly-fetched figure as of the research date. The
  March figure is noted here only as historical context, not used
  elsewhere in the project.
  Source: [SI.com/OnSI — "How Much Cap Space Broncos Have After Free Agency"](https://www.si.com/nfl/broncos/onsi/news/how-much-cap-space-broncos-have-after-free-agency-2026)
  (single-sourced, dated March 31, 2026).

## Key Contracts (Top 2026 Cap Hits)

Cross-checked between the OTC live page and the project's scraped
`data/raw/contracts/den_2026.csv` — all figures below matched exactly
between the two sources (confirms the scrape is accurate).

| Player | Position | 2026 Cap Hit | Source |
|---|---|---|---|
| Mike McGlinchey | Right Tackle | $23,775,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Zach Allen | Interior DL | $16,477,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| D.J. Jones | Interior DL | $14,570,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Evan Engram | Tight End | $14,136,666 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Courtland Sutton | Wide Receiver | $13,975,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Talanoa Hufanga | Safety | $13,500,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Patrick Surtain II | Cornerback | $12,698,400 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Ben Powers | Left Guard | $10,600,000 | [OTC](https://overthecap.com/salary-cap/denver-broncos); matches `den_2026.csv` |
| Quinn Meinerz | Center | $9,208,200 | [OTC](https://overthecap.com/salary-cap/denver-broncos) |
| Nik Bonitto | Edge Rusher | $8,421,200 | [OTC](https://overthecap.com/salary-cap/denver-broncos) |

No discrepancies found between OTC and the scraped `den_2026.csv` for
any of the top 8 cap hits the task brief called out.

## Dead Money

- **Total 2026 dead money: $3,512,701**
  Source: [Over The Cap — Denver Broncos Salary Cap](https://overthecap.com/salary-cap/denver-broncos)
  (live page, fetched 2026-08-27). This is the current, resolved figure
  and should be treated as authoritative.
- Context (single-sourced, not used to override the figure above): an
  SI.com/OnSI article dated March 31, 2026 discussed LB Dre Greenlaw's
  release and noted he "carries his full cap charge of about $8.2M until
  June 1" under a post-June-1 designation — meaning only part of that
  charge hit the 2026 cap immediately, with the rest deferring to 2027.
  This mechanic is consistent with the 2026 dead money total settling
  lower than $8.2M alone by the time of this research (August).
  Source: [SI.com/OnSI — "How Much Cap Space Broncos Have After Free Agency"](https://www.si.com/nfl/broncos/onsi/news/how-much-cap-space-broncos-have-after-free-agency-2026)
  (single-sourced).

## Roster Needs

Ranked list of draft/roster priorities per a single SI.com/OnSI article;
marked single-sourced since no second outlet's ranked list was
cross-verified. Top 3 are the ones most consistently echoed across other
search results (WebSearch snippets on running back and safety needs from
additional, unfetched outlets).

1. **Inside Linebacker** — Dre Greenlaw was released; only Alex Singleton
   and Justin Strnad remain as options, both over 30 by season start.
2. **Tight End** — position graded among the NFL's worst in 2025 despite
   re-signing current depth (Trautman, Adkins, Krull).
3. **Running Back** — insurance behind J.K. Dobbins needed given his
   injury history.

Additional needs mentioned (lower priority per the same source): D-line
depth (after John Franklin-Myers's departure), safety (after P.J. Locke's
departure and Brandon Jones entering a contract year), and offensive
line depth behind an aging tackle group.

Source: [SI.com/OnSI — "Broncos' Key Needs Ranked Ahead of the 2026 NFL Draft"](https://www.si.com/nfl/broncos/onsi/news/broncos-key-needs-ranked-ahead-of-2026-nfl-draft)
(single-sourced).

## Recent Signings

Source: [DenverBroncos.com — "2026 Denver Broncos Free Agency Tracker"](https://www.denverbroncos.com/news/2026-denver-broncos-free-agency-tracker)
(official team site tracker).

**Trade acquisition:**
- WR Jaylen Waddle — acquired from the Miami Dolphins for a 2026 1st-round
  pick (No. 30), 3rd-round pick (No. 94), and 4th-round pick (No. 130);
  Denver received Waddle plus a 2026 4th-round pick (No. 111). Waddle's
  $4,878,200 2026 cap hit in `data/raw/contracts/den_2026.csv` is
  consistent with him being on Denver's roster post-trade.

**Re-signings:**
| Player | Position | Contract Length |
|---|---|---|
| J.K. Dobbins | RB | 2 years |
| Alex Singleton | ILB | 2 years |
| Justin Strnad | ILB | 3 years |
| Adam Trautman | TE | 3 years |
| Alex Palczewski | OL | 2 years |
| Nate Adkins | TE | 1 year |
| Sam Ehlinger | QB | 1 year |
| Lucas Krull | TE | 1 year |
| Lil'Jordan Humphrey | WR | 1 year |
| Adam Prentice | FB | 1 year |
| Jaleel McLaughlin | RB | 1 year |

**Free agent signing:**
- S Tycen Anderson — 1 year.

**Tender:**
- CB Ja'Quan McMillian — signed second-round RFA tender.

## Sources Consulted

- https://overthecap.com/salary-cap/denver-broncos (primary, live fetch)
- https://www.denverbroncos.com/news/2026-denver-broncos-free-agency-tracker
- https://www.si.com/nfl/broncos/onsi/news/broncos-key-needs-ranked-ahead-of-2026-nfl-draft
- https://www.si.com/nfl/broncos/onsi/news/how-much-cap-space-broncos-have-after-free-agency-2026
- https://www.spotrac.com/nfl/denver-broncos/cap/_/year/2026 (attempted, returned HTTP 403 — not used)
