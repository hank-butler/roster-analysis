# AI Agent Layer Design
**Date:** 2026-06-15
**Priority:** 4 — AI Agent Layer
**Goal:** Multi-agent system using the Claude API that answers natural language NFL roster questions, grounded in real pipeline data. Headline feature for the SF 49ers Football AI Fellow portfolio.

---

## Architecture

```
src/agents/
├── __init__.py          # exports AgentSystem
├── agent_system.py      # top-level entry point
├── coordinator_agent.py # LLM-based query routing
├── contract_agent.py    # cap/valuation analysis
├── scouting_agent.py    # player scouting reports
└── strategy_agent.py    # game strategy + roster construction
```

**Routing pattern:** Coordinator classifies query → dispatches to one specialist → returns structured response. Two API calls per query (one tiny classification call, one full response call). Stateless — no conversation history.

**Model:** `claude-sonnet-4-6` for all calls.

---

## Entry Point — `agent_system.py`

**Class:** `AgentSystem`

```python
class AgentSystem:
    def __init__(
        self,
        players: Optional[List[PlayerAsset]] = None,
        api_key: Optional[str] = None,
    ) -> None
```

- `players=None` → loads from `data/processed/player_assets_ready.csv` and values via `PlayerValuationModel`
- `players=<list>` → uses pre-loaded, pre-valued assets (dashboard pre-loads once)
- `api_key=None` → reads `ANTHROPIC_API_KEY` environment variable; raises `ValueError` if missing

**Public method:**

```python
def ask(self, query: str) -> Dict[str, object]:
    # Returns:
    # {
    #   "query":     str,        # original query
    #   "agent":     str,        # "contract" | "scouting" | "strategy" | "error"
    #   "response":  str,        # Claude's natural language answer
    #   "data_used": List[str],  # top player names injected as context
    # }
```

On any `anthropic.APIError`: catches exception, returns `{"agent": "error", "response": "Agent encountered an error: <msg>", "data_used": []}` — never crashes the caller.

---

## Coordinator — `coordinator_agent.py`

**Class:** `CoordinatorAgent`

```python
class CoordinatorAgent:
    CATEGORIES = ("contract", "scouting", "strategy")
    DEFAULT_FALLBACK = "scouting"

    def __init__(self, client: anthropic.Anthropic) -> None

    def route(self, query: str) -> str:
        # Returns: "contract" | "scouting" | "strategy"
```

**Classification prompt:** minimal, asks Claude to return exactly one word. No player data injected — just the query text.

```
System: You are a routing classifier for an NFL analytics system.
        Classify the user query into exactly one category:
        - contract: cap space, salary, valuations, overvalued/undervalued players
        - scouting: player reports, stats, performance, injuries, age
        - strategy: roster construction, free agency, draft, division comparison, SB template
        Reply with only one word: contract, scouting, or strategy.

User: <query>
```

If Claude returns anything other than the three valid categories (e.g. "unknown", multi-word response, empty): logs a warning and returns `DEFAULT_FALLBACK = "scouting"`.

---

## Specialist Agents

All three share the interface:
```python
def __init__(self, client: anthropic.Anthropic) -> None

def run(self, query: str, players: List[PlayerAsset]) -> Dict[str, object]
```

`AgentSystem` creates **one** `anthropic.Anthropic` client at init and passes it to the coordinator and all three specialists — no specialist creates its own client. Returns the same dict shape as `AgentSystem.ask()`.

### `ContractAgent` — `contract_agent.py`

**Data injected:** per-player financial table, SF players first, then other teams if query mentions them.

Columns formatted as plain text: `name | position | cap_hit | fair_value | efficiency_ratio | sharpe_ratio | overvalued_flag`

Capped at 30 players to stay within context limits. Logs at DEBUG which players were included.

**System prompt role:** NFL cap analyst who uses a bond-pricing valuation model. Answers must cite specific numbers from the injected data. Never hallucinate contract values.

**`data_used`:** names of all players whose rows were injected.

### `ScoutingAgent` — `scouting_agent.py`

**Data injected:** per-player performance table.

Columns: `name | position | age | epa_total | snaps_played | games_missed`

Filters to players matching the query where possible (e.g., if "Kittle" is in the query, prioritize TE rows). Falls back to full SF roster if no match found. Capped at 30 players.

**System prompt role:** NFL scout who writes plain-English reports for coaches and GMs, not data scientists. Translates EPA numbers into plain language (e.g., "consistently above-average in pass-catching situations").

**`data_used`:** names of players whose rows were injected.

### `StrategyAgent` — `strategy_agent.py`

**Data injected:** team-level summaries rather than individual player rows. Built using `DivisionAnalyzer` (already built in Priority 3):
- `compare_portfolio_metrics()` — efficiency, risk, Sharpe per team
- `compare_position_allocation()` — cap % by position group for all 4 NFC West teams
- `SuperBowlTemplateAnalyzer.calculate_similarity_score()` — SF's structural gaps vs SB winners

`DivisionAnalyzer` is instantiated inside `StrategyAgent.run()` using the `players` list split by team.

Formatted as a compact team comparison table + SB template gap list.

**System prompt role:** strategic roster advisor who thinks in terms of portfolio construction, cap efficiency, and competitive positioning within the NFC West.

**`data_used`:** team names included in the summary (`["SF", "SEA", "LAR", "ARI"]`). Note: unlike the other two agents, `data_used` here contains team abbreviations rather than player names — this is intentional since the strategy agent works at the team level.

---

## Testing

All tests mock `anthropic.Anthropic` — no real API calls. Tests live in `tests/test_agent_system.py`.

**What to test:**
1. `AgentSystem` raises `ValueError` when API key is missing
2. `AgentSystem` loads from CSV when `players=None` (mock CSV path)
3. `CoordinatorAgent.route()` returns correct category for clear queries (mocked API response)
4. `CoordinatorAgent.route()` falls back to `"scouting"` on unexpected API response
5. Each specialist's `run()` returns dict with correct keys: `query`, `agent`, `response`, `data_used`
6. `data_used` is a list of strings
7. API error → returns error dict, does not raise
8. `AgentSystem.ask()` end-to-end with fully mocked API (coordinator + specialist)

---

## Error Handling

| Situation | Behaviour |
|---|---|
| `ANTHROPIC_API_KEY` not set | `ValueError` at `__init__` time with clear message |
| `api_key` param provided directly | used as-is (overrides env var) |
| `anthropic.APIError` during any call | caught, returns error dict, logs warning |
| Coordinator returns unexpected category | logs warning, falls back to `"scouting"` |
| `player_assets_ready.csv` not found | `FileNotFoundError` with hint to run `collect_all_data.py` |
| `players` list is empty | logs warning, agents return a polite "no data available" response |

---

## Key Constraints

- Model: `claude-sonnet-4-6` for all calls
- No `print()` — use `logging`; agents log injected data at `DEBUG` level
- Absolute imports throughout (`from src.player_valuation import ...`)
- Google-style docstrings with `Args:` and `Returns:` on all public methods
- No Streamlit calls — pure Python, consumable by both Streamlit and CLI
- Never hallucinate stats: every numerical claim in a response must come from injected context
- `agent_system.py` has an `if __name__ == "__main__":` demo that reads from CSV and runs one sample query per agent type
- Anthropic SDK must be installed: `pip install anthropic`

---

## Dependencies

New: `anthropic` Python SDK (to be added to `requirements.txt`)

Imports from existing project:
- `src.player_valuation.PlayerAsset`, `PlayerValuationModel`, `PortfolioAnalyzer`
- `src.sb_template.SuperBowlTemplateAnalyzer`
- `src.nfc_west_comparison.DivisionAnalyzer` (strategy agent only)
