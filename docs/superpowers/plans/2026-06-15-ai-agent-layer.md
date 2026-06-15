# AI Agent Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 5-file multi-agent system that answers natural language NFL roster questions grounded in real pipeline data, using LLM-based routing via the Claude API.

**Architecture:** `AgentSystem` (entry point) creates one `anthropic.Anthropic` client, passes it to `CoordinatorAgent` (routes query) and three specialist agents (`ContractAgent`, `ScoutingAgent`, `StrategyAgent`). Two API calls per query: coordinator classifies into one word, specialist answers with player data injected as context. Stateless — no conversation history.

**Tech Stack:** Python 3.11, `anthropic` SDK (`claude-sonnet-4-6`), pandas, pytest with `unittest.mock`. Conda env: `nfl_analytics`. All commands run from `/home/hankbutler/Desktop/Projects/roster-analysis`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/agents/__init__.py` | Create | Exports `AgentSystem` |
| `src/agents/coordinator_agent.py` | Create | LLM routing: classifies query → `"contract" \| "scouting" \| "strategy"` |
| `src/agents/contract_agent.py` | Create | Cap/valuation analysis with financial table context |
| `src/agents/scouting_agent.py` | Create | Player scouting reports with performance table context |
| `src/agents/strategy_agent.py` | Create | Team strategy using `DivisionAnalyzer` team-level summaries |
| `src/agents/agent_system.py` | Create | Entry point: loads data, wires agents, exposes `ask()` |
| `requirements.txt` | Modify | Add `anthropic` |
| `tests/test_agent_system.py` | Create | All tests (mocked API — no real calls) |

---

## Shared mock helper (used in all test steps)

Every test step that needs a mock client uses this helper defined at the top of `tests/test_agent_system.py`:

```python
from unittest.mock import MagicMock
import anthropic

def _mock_client(response_text: str) -> MagicMock:
    """Return a mock anthropic.Anthropic client that returns response_text."""
    client = MagicMock(spec=anthropic.Anthropic)
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client

def _error_client() -> MagicMock:
    """Return a mock client that raises APIConnectionError on every call."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    return client
```

---

### Task 1: Install `anthropic` + `CoordinatorAgent`

**Files:**
- Modify: `requirements.txt`
- Create: `src/agents/__init__.py`
- Create: `src/agents/coordinator_agent.py`
- Create: `tests/test_agent_system.py` (coordinator tests only for now)

- [ ] **Step 1: Install anthropic and update requirements.txt**

```bash
conda run -n nfl_analytics pip install anthropic
```

Add to `requirements.txt` under `# Utilities`:
```
anthropic>=0.25.0
```

Verify:
```bash
conda run -n nfl_analytics python -c "import anthropic; print(anthropic.__version__)"
```
Expected: a version string like `0.25.0` or higher.

- [ ] **Step 2: Write failing coordinator tests**

Create `tests/test_agent_system.py`:

```python
import pytest
from unittest.mock import MagicMock
import anthropic

from src.agents.coordinator_agent import CoordinatorAgent


# ---- Shared helpers -------------------------------------------------------

def _mock_client(response_text: str) -> MagicMock:
    """Return a mock anthropic.Anthropic that returns response_text."""
    client = MagicMock(spec=anthropic.Anthropic)
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def _error_client() -> MagicMock:
    """Return a mock client that raises APIConnectionError."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    return client


# ---- CoordinatorAgent -----------------------------------------------------

def test_coordinator_routes_contract_query():
    coordinator = CoordinatorAgent(client=_mock_client("contract"))
    assert coordinator.route("Who is our most overvalued player?") == "contract"


def test_coordinator_routes_scouting_query():
    coordinator = CoordinatorAgent(client=_mock_client("scouting"))
    assert coordinator.route("Generate a scouting report on George Kittle") == "scouting"


def test_coordinator_routes_strategy_query():
    coordinator = CoordinatorAgent(client=_mock_client("strategy"))
    assert coordinator.route("What positions should we target in free agency?") == "strategy"


def test_coordinator_fallback_on_unexpected_response():
    coordinator = CoordinatorAgent(client=_mock_client("unknown category"))
    result = coordinator.route("some ambiguous query")
    assert result == "scouting"  # DEFAULT_FALLBACK


def test_coordinator_fallback_on_empty_response():
    coordinator = CoordinatorAgent(client=_mock_client(""))
    result = coordinator.route("anything")
    assert result == "scouting"


def test_coordinator_strips_whitespace_from_response():
    coordinator = CoordinatorAgent(client=_mock_client("  contract  \n"))
    assert coordinator.route("cap space?") == "contract"
```

- [ ] **Step 3: Run to confirm tests fail**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'src.agents.coordinator_agent'`

- [ ] **Step 4: Create `src/agents/__init__.py`**

```python
from src.agents.agent_system import AgentSystem

__all__ = ["AgentSystem"]
```

- [ ] **Step 5: Create `src/agents/coordinator_agent.py`**

```python
import logging
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

_ROUTING_SYSTEM_PROMPT = """You are a routing classifier for an NFL analytics system.
Classify the user query into exactly one category:
- contract: cap space, salary, valuations, overvalued/undervalued players
- scouting: player reports, stats, performance, injuries, age
- strategy: roster construction, free agency, draft, division comparison, SB template
Reply with only one word: contract, scouting, or strategy."""

_MODEL = "claude-sonnet-4-6"


class CoordinatorAgent:
    """Routes natural language NFL queries to the appropriate specialist agent.

    Makes a single lightweight Claude API call that returns one classification word.
    Falls back to 'scouting' on any unexpected response.
    """

    CATEGORIES = ("contract", "scouting", "strategy")
    DEFAULT_FALLBACK = "scouting"

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def route(self, query: str) -> str:
        """Classify a query into one specialist category.

        Args:
            query: Natural language NFL question from the user.

        Returns:
            One of 'contract', 'scouting', or 'strategy'.
        """
        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=10,
            system=_ROUTING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
        )
        category = response.content[0].text.strip().lower()
        if category not in self.CATEGORIES:
            logger.warning(
                "Coordinator returned unexpected category '%s' — falling back to '%s'",
                category,
                self.DEFAULT_FALLBACK,
            )
            return self.DEFAULT_FALLBACK
        return category
```

- [ ] **Step 6: Run coordinator tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -v
```
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/agents/__init__.py src/agents/coordinator_agent.py \
        tests/test_agent_system.py
git commit -m "feat: add CoordinatorAgent with LLM-based query routing"
```

---

### Task 2: `ContractAgent`

**Files:**
- Create: `src/agents/contract_agent.py`
- Modify: `tests/test_agent_system.py` (append contract tests)

- [ ] **Step 1: Write failing contract agent tests**

Append to `tests/test_agent_system.py`:

```python
from src.player_valuation import PlayerAsset, PlayerValuationModel
from src.agents.contract_agent import ContractAgent


def _make_valued_player(
    name: str, position: str, cap_hit: float, age: int, team: str = "SF"
) -> PlayerAsset:
    p = PlayerAsset(
        player_id=f"{team.lower()}_{position.lower()}_{name.lower().replace(' ', '_')}",
        name=name, position=position, team=team, age=age,
        cap_hit_2026=cap_hit, years_remaining=2,
        guaranteed_money=cap_hit * 0.5, total_contract_value=cap_hit * 3,
        epa_total=10.0, snaps_played=800, games_missed=1,
    )
    return PlayerValuationModel().value_roster([p])[0]


@pytest.fixture
def sf_players():
    return [
        _make_valued_player("Brock Purdy", "QB", 23_700_000, 27),
        _make_valued_player("Nick Bosa", "DL", 22_990_000, 29),
        _make_valued_player("George Kittle", "TE", 14_100_000, 31),
    ]


def test_contract_agent_returns_required_keys(sf_players):
    agent = ContractAgent(client=_mock_client("Brock Purdy is overvalued."))
    result = agent.run("Who is overvalued?", sf_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_contract_agent_sets_agent_name(sf_players):
    agent = ContractAgent(client=_mock_client("Analysis here."))
    result = agent.run("any query", sf_players)
    assert result["agent"] == "contract"


def test_contract_agent_data_used_is_list_of_strings(sf_players):
    agent = ContractAgent(client=_mock_client("Response text."))
    result = agent.run("cap analysis", sf_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_contract_agent_data_used_contains_player_names(sf_players):
    agent = ContractAgent(client=_mock_client("Response."))
    result = agent.run("any", sf_players)
    # data_used should be the player names whose rows were injected
    assert "Brock Purdy" in result["data_used"]


def test_contract_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_contract_agent_query_echoed_in_result(sf_players):
    agent = ContractAgent(client=_mock_client("ok"))
    result = agent.run("Who is the most overvalued?", sf_players)
    assert result["query"] == "Who is the most overvalued?"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "contract" -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'src.agents.contract_agent'`

- [ ] **Step 3: Create `src/agents/contract_agent.py`**

```python
import logging
from typing import Dict, List, object as object_

import anthropic

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_PLAYERS = 30

_SYSTEM_PROMPT = """You are an NFL cap analyst for the San Francisco 49ers.
You use a bond-pricing valuation model to assess player contracts.
Key metrics provided:
- Cap Hit: annual salary cap charge
- Fair Value: what the player's performance justifies
- Efficiency: expected value / cap hit (>1.0 = good value)
- Sharpe: risk-adjusted return (higher = better)
- Status: Overvalued / Undervalued / Fair

Answer the user's question using ONLY the data provided below.
Cite specific numbers. Never invent contract figures not in the data.
Write for a front office audience — professional, concise, actionable."""


def _overvalued_flag(player: PlayerAsset) -> str:
    if player.cap_hit_2026 > player.fair_value * 1.15 and player.fair_value > 0:
        return "Overvalued"
    if player.fair_value > player.cap_hit_2026 * 1.15:
        return "Undervalued"
    return "Fair"


def _format_player_row(p: PlayerAsset) -> str:
    return (
        f"{p.name} | {p.position} | "
        f"${p.cap_hit_2026:,.0f} | "
        f"${p.fair_value:,.0f} | "
        f"{p.efficiency_ratio:.2f} | "
        f"{p.sharpe_ratio:.2f} | "
        f"{_overvalued_flag(p)}"
    )


class ContractAgent:
    """Answers cap and contract analysis questions grounded in valuation model data."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a contract analysis query grounded in player data.

        Prioritises SF players, caps context at 30 players.

        Args:
            query: Natural language contract question.
            players: Pre-valued list of PlayerAsset objects.

        Returns:
            Dict with keys: query, agent, response, data_used.
        """
        # SF first, then other teams; cap at 30
        sf = [p for p in players if p.team == "SF"]
        others = [p for p in players if p.team != "SF"]
        selected = (sf + others)[:_MAX_PLAYERS]

        header = "Name | Position | Cap Hit | Fair Value | Efficiency | Sharpe | Status"
        rows = [_format_player_row(p) for p in selected]
        data_block = "\n".join([header] + rows)

        logger.debug("ContractAgent injecting %d players into context", len(selected))

        full_prompt = f"PLAYER CONTRACT DATA:\n{data_block}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "contract",
            "response": response.content[0].text,
            "data_used": [p.name for p in selected],
        }
```

- [ ] **Step 4: Run contract tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "contract" -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/agents/contract_agent.py tests/test_agent_system.py
git commit -m "feat: add ContractAgent with financial table context"
```

---

### Task 3: `ScoutingAgent`

**Files:**
- Create: `src/agents/scouting_agent.py`
- Modify: `tests/test_agent_system.py` (append scouting tests)

- [ ] **Step 1: Write failing scouting agent tests**

Append to `tests/test_agent_system.py`:

```python
from src.agents.scouting_agent import ScoutingAgent


def test_scouting_agent_returns_required_keys(sf_players):
    agent = ScoutingAgent(client=_mock_client("Kittle is elite."))
    result = agent.run("Scouting report on George Kittle", sf_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_scouting_agent_sets_agent_name(sf_players):
    agent = ScoutingAgent(client=_mock_client("Report."))
    result = agent.run("any", sf_players)
    assert result["agent"] == "scouting"


def test_scouting_agent_data_used_is_list_of_strings(sf_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", sf_players)
    assert isinstance(result["data_used"], list)
    assert all(isinstance(n, str) for n in result["data_used"])


def test_scouting_agent_prioritises_name_match(sf_players):
    """When query mentions a player name, that player should appear in data_used."""
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Tell me about George Kittle", sf_players)
    assert "George Kittle" in result["data_used"]


def test_scouting_agent_caps_at_30_players():
    players = [
        _make_valued_player(f"Player {i}", "WR", 5_000_000, 25)
        for i in range(50)
    ]
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("any", players)
    assert len(result["data_used"]) <= 30


def test_scouting_agent_query_echoed(sf_players):
    agent = ScoutingAgent(client=_mock_client("ok"))
    result = agent.run("Is Bosa injury-prone?", sf_players)
    assert result["query"] == "Is Bosa injury-prone?"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "scouting" -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'src.agents.scouting_agent'`

- [ ] **Step 3: Create `src/agents/scouting_agent.py`**

```python
import logging
from typing import Dict, List

import anthropic

from src.player_valuation import PlayerAsset

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_PLAYERS = 30

_SYSTEM_PROMPT = """You are a senior NFL scout for the San Francisco 49ers.
You write scouting reports and player assessments for coaches and general managers.
Write in plain English — translate stats into insights, not just numbers.
Guidelines:
- EPA (Expected Points Added): >15 = elite, 5-15 = above average, <5 = below average
- Games missed: 0-2 = durable, 3-6 = some concern, 7+ = significant injury risk
- Snaps played: indicates how central the player is to the scheme
Answer using ONLY the data provided below. Never invent stats not in the data."""


def _format_player_row(p: PlayerAsset) -> str:
    return (
        f"{p.name} | {p.position} | Age {p.age} | "
        f"EPA {p.epa_total:.1f} | "
        f"Snaps {p.snaps_played} | "
        f"Games missed {p.games_missed}"
    )


class ScoutingAgent:
    """Answers player scouting and performance questions grounded in stats data."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def _select_players(
        self, query: str, players: List[PlayerAsset]
    ) -> List[PlayerAsset]:
        """Select up to 30 players, prioritising name matches in the query."""
        query_lower = query.lower()
        matched = [p for p in players if p.name.lower() in query_lower]
        others = [p for p in players if p.name.lower() not in query_lower]
        # SF players first within each group
        sf_matched = [p for p in matched if p.team == "SF"]
        other_matched = [p for p in matched if p.team != "SF"]
        sf_others = [p for p in others if p.team == "SF"]
        rest = [p for p in others if p.team != "SF"]
        ordered = sf_matched + other_matched + sf_others + rest
        return ordered[:_MAX_PLAYERS]

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a scouting query grounded in player performance data.

        Args:
            query: Natural language scouting question.
            players: Pre-valued list of PlayerAsset objects.

        Returns:
            Dict with keys: query, agent, response, data_used.
        """
        selected = self._select_players(query, players)

        header = "Name | Position | Age | EPA Total | Snaps Played | Games Missed"
        rows = [_format_player_row(p) for p in selected]
        data_block = "\n".join([header] + rows)

        logger.debug("ScoutingAgent injecting %d players into context", len(selected))

        full_prompt = f"PLAYER SCOUTING DATA:\n{data_block}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "scouting",
            "response": response.content[0].text,
            "data_used": [p.name for p in selected],
        }
```

- [ ] **Step 4: Run scouting tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "scouting" -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/agents/scouting_agent.py tests/test_agent_system.py
git commit -m "feat: add ScoutingAgent with performance table context"
```

---

### Task 4: `StrategyAgent`

**Files:**
- Create: `src/agents/strategy_agent.py`
- Modify: `tests/test_agent_system.py` (append strategy tests)

- [ ] **Step 1: Write failing strategy agent tests**

Append to `tests/test_agent_system.py`:

```python
from src.agents.strategy_agent import StrategyAgent


@pytest.fixture
def multi_team_players():
    """Players from multiple NFC West teams for StrategyAgent."""
    sf = [_make_valued_player(f"SF Player {i}", pos, 10_000_000, 27, "SF")
          for i, pos in enumerate(["QB", "WR", "DL"])]
    sea = [_make_valued_player(f"SEA Player {i}", pos, 8_000_000, 28, "SEA")
           for i, pos in enumerate(["QB", "WR"])]
    return sf + sea


def test_strategy_agent_returns_required_keys(multi_team_players):
    agent = StrategyAgent(client=_mock_client("Focus on pass rush."))
    result = agent.run("What should we prioritise in free agency?", multi_team_players)
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_strategy_agent_sets_agent_name(multi_team_players):
    agent = StrategyAgent(client=_mock_client("Strategy response."))
    result = agent.run("any", multi_team_players)
    assert result["agent"] == "strategy"


def test_strategy_agent_data_used_contains_team_names(multi_team_players):
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("how do we compare?", multi_team_players)
    assert isinstance(result["data_used"], list)
    # data_used contains team abbreviations for strategy agent
    assert all(isinstance(t, str) for t in result["data_used"])
    assert len(result["data_used"]) > 0


def test_strategy_agent_query_echoed(multi_team_players):
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("How do we compare to the SB template?", multi_team_players)
    assert result["query"] == "How do we compare to the SB template?"


def test_strategy_agent_handles_single_team_data():
    """Should not crash when only one team's data is available."""
    sf_only = [_make_valued_player(f"P {i}", "QB", 10_000_000, 27, "SF")
               for i in range(3)]
    agent = StrategyAgent(client=_mock_client("ok"))
    result = agent.run("what should we do?", sf_only)
    assert result["agent"] == "strategy"
    assert "response" in result
```

- [ ] **Step 2: Run to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "strategy" -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'src.agents.strategy_agent'`

- [ ] **Step 3: Create `src/agents/strategy_agent.py`**

```python
import logging
from typing import Dict, List

import anthropic

from src.nfc_west_comparison import DivisionAnalyzer
from src.player_valuation import PlayerAsset
from src.sb_template import SuperBowlTemplateAnalyzer

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are a strategic roster advisor for the San Francisco 49ers.
You think in terms of cap allocation, portfolio efficiency, and competitive positioning.
Use the team comparison data below to inform specific, actionable recommendations.
Focus on: cap allocation gaps vs SB winners, division strengths and weaknesses,
and free agency / draft priorities.
Answer using ONLY the data provided. Be concise and front-office appropriate."""


class StrategyAgent:
    """Answers team strategy questions using DivisionAnalyzer team-level summaries."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        """Initialise with a shared Anthropic client.

        Args:
            client: Pre-initialised anthropic.Anthropic client.
        """
        self._client = client

    def _build_context(self, players: List[PlayerAsset]) -> tuple:
        """Build team-level context string and list of teams present.

        Args:
            players: Pre-valued list of PlayerAsset objects across all teams.

        Returns:
            Tuple of (context_string, list_of_team_abbreviations).
        """
        # Split players by team
        teams_data: Dict[str, List[PlayerAsset]] = {}
        for p in players:
            teams_data.setdefault(p.team, []).append(p)

        team_list = sorted(teams_data.keys())

        if not teams_data:
            return "No team data available.", []

        # Build context using DivisionAnalyzer (handles 1+ teams gracefully)
        try:
            analyzer = DivisionAnalyzer(teams_data)
            metrics_df = analyzer.compare_portfolio_metrics()
            alloc_df = analyzer.compare_position_allocation()

            metrics_text = metrics_df.to_string(index=False)
            alloc_text = alloc_df.to_string()

            # SB similarity for SF if present
            sb_lines = []
            if "SF" in teams_data:
                sb_analyzer = SuperBowlTemplateAnalyzer()
                sim = sb_analyzer.calculate_similarity_score(teams_data["SF"])
                sb_lines.append(
                    f"SF SB Template Similarity: {sim['overall_similarity']:.1f}/100"
                )
                for gap in sim["gaps"]:
                    sb_lines.append(f"  Gap: {gap}")

            sections = [
                "TEAM PORTFOLIO METRICS:",
                metrics_text,
                "",
                "CAP ALLOCATION BY POSITION GROUP (% of cap):",
                alloc_text,
            ]
            if sb_lines:
                sections += ["", "SF vs SB TEMPLATE:"] + sb_lines

            context = "\n".join(sections)
        except Exception as exc:
            logger.warning("DivisionAnalyzer failed: %s — using minimal context", exc)
            context = f"Teams present: {', '.join(team_list)}"

        return context, team_list

    def run(
        self, query: str, players: List[PlayerAsset]
    ) -> Dict[str, object]:
        """Answer a strategy query using team-level portfolio summaries.

        Args:
            query: Natural language strategy question.
            players: Pre-valued list of PlayerAsset objects (may span multiple teams).

        Returns:
            Dict with keys: query, agent, response, data_used.
            Note: data_used contains team abbreviations, not player names.
        """
        context, teams = self._build_context(players)
        logger.debug("StrategyAgent building context for teams: %s", teams)

        full_prompt = f"{context}\n\nQUESTION: {query}"

        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )

        return {
            "query": query,
            "agent": "strategy",
            "response": response.content[0].text,
            "data_used": teams,
        }
```

- [ ] **Step 4: Run strategy tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "strategy" -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/agents/strategy_agent.py tests/test_agent_system.py
git commit -m "feat: add StrategyAgent with DivisionAnalyzer team-level context"
```

---

### Task 5: `AgentSystem` (entry point + integration tests)

**Files:**
- Create: `src/agents/agent_system.py`
- Modify: `tests/test_agent_system.py` (append AgentSystem tests)

- [ ] **Step 1: Write failing AgentSystem tests**

Append to `tests/test_agent_system.py`:

```python
import os
from unittest.mock import MagicMock, patch

from src.agents.agent_system import AgentSystem


# ---- AgentSystem: constructor ---------------------------------------------

def test_agent_system_raises_if_no_api_key(sf_players, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AgentSystem(players=sf_players, api_key=None)


def test_agent_system_accepts_api_key_param(sf_players):
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _mock_client("contract")
        system = AgentSystem(players=sf_players, api_key="sk-test-key")
    assert system is not None


def test_agent_system_accepts_pre_loaded_players(sf_players):
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _mock_client("contract")
        system = AgentSystem(players=sf_players, api_key="sk-test")
    assert system._players is not None
    assert len(system._players) == len(sf_players)


def test_agent_system_loads_from_csv_when_no_players(tmp_path, monkeypatch):
    """When players=None, AgentSystem loads from player_assets_ready.csv."""
    import pandas as pd
    from src.player_valuation import PlayerAsset

    # Create a minimal CSV in tmp_path
    csv_path = tmp_path / "player_assets_ready.csv"
    pd.DataFrame([{
        "player_id": "sf_qb_test", "name": "Test QB", "position": "QB",
        "team": "SF", "age": 27, "cap_hit_2026": 20_000_000,
        "years_remaining": 3, "guaranteed_money": 10_000_000,
        "total_contract_value": 60_000_000, "epa_total": 30.0,
        "snaps_played": 1000, "games_missed": 0,
    }]).to_csv(csv_path, index=False)

    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = _mock_client("contract")
        with patch(
            "src.agents.agent_system._CSV_PATH",
            str(csv_path),
        ):
            system = AgentSystem(players=None, api_key="sk-test")

    assert len(system._players) == 1
    assert system._players[0].name == "Test QB"


# ---- AgentSystem: ask() ---------------------------------------------------

def _make_system_with_mock(sf_players, route_response: str, agent_response: str):
    """Helper: builds AgentSystem with two mocked API calls."""
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        text = route_response if call_count == 1 else agent_response
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        return msg

    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = side_effect

    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = client
        system = AgentSystem(players=sf_players, api_key="sk-test")

    return system


def test_ask_returns_required_keys(sf_players):
    system = _make_system_with_mock(sf_players, "contract", "Purdy is overvalued.")
    result = system.ask("Who is most overvalued?")
    assert set(result.keys()) == {"query", "agent", "response", "data_used"}


def test_ask_routes_to_contract_agent(sf_players):
    system = _make_system_with_mock(sf_players, "contract", "Cap analysis here.")
    result = system.ask("Who is overvalued?")
    assert result["agent"] == "contract"


def test_ask_routes_to_scouting_agent(sf_players):
    system = _make_system_with_mock(sf_players, "scouting", "Kittle is elite.")
    result = system.ask("Tell me about Kittle")
    assert result["agent"] == "scouting"


def test_ask_routes_to_strategy_agent(sf_players):
    system = _make_system_with_mock(sf_players, "strategy", "Target pass rush.")
    result = system.ask("What positions should we target?")
    assert result["agent"] == "strategy"


def test_ask_returns_error_dict_on_api_error(sf_players):
    """API error → returns error dict, does not raise."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    with patch("src.agents.agent_system.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value = client
        system = AgentSystem(players=sf_players, api_key="sk-test")

    result = system.ask("any question")
    assert result["agent"] == "error"
    assert "error" in result["response"].lower()
    assert result["data_used"] == []


def test_ask_echoes_query(sf_players):
    system = _make_system_with_mock(sf_players, "scouting", "response")
    result = system.ask("Is Bosa healthy?")
    assert result["query"] == "Is Bosa healthy?"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -k "agent_system or ask or system" -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'src.agents.agent_system'`

- [ ] **Step 3: Create `src/agents/agent_system.py`**

```python
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
import pandas as pd

from src.agents.contract_agent import ContractAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.scouting_agent import ScoutingAgent
from src.agents.strategy_agent import StrategyAgent
from src.player_valuation import PlayerAsset, PlayerValuationModel

logger = logging.getLogger(__name__)

_CSV_PATH = "data/processed/player_assets_ready.csv"


def _load_players_from_csv(path: str) -> List[PlayerAsset]:
    """Load and value players from the processed CSV.

    Args:
        path: Path to player_assets_ready.csv.

    Returns:
        List of valued PlayerAsset objects.

    Raises:
        FileNotFoundError: If the CSV does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Run: python collect_all_data.py"
        )
    df = pd.read_csv(p)
    players = []
    for _, row in df.iterrows():
        try:
            players.append(PlayerAsset(
                player_id=str(row["player_id"]),
                name=str(row["name"]),
                position=str(row["position"]),
                team=str(row["team"]),
                age=int(row["age"]),
                cap_hit_2026=float(row["cap_hit_2026"]),
                years_remaining=int(row["years_remaining"]),
                guaranteed_money=float(row["guaranteed_money"]),
                total_contract_value=float(row["total_contract_value"]),
                epa_total=float(row["epa_total"]),
                snaps_played=int(row["snaps_played"]),
                games_missed=int(row["games_missed"]),
            ))
        except Exception as exc:
            logger.warning("Skipping row for %s: %s", row.get("name", "?"), exc)

    model = PlayerValuationModel()
    valued = model.value_roster(players)
    logger.info("Loaded and valued %d players from %s", len(valued), path)
    return valued


class AgentSystem:
    """Top-level entry point for the multi-agent NFL analytics system.

    Creates one shared Anthropic client, routes queries via CoordinatorAgent,
    and dispatches to the appropriate specialist (Contract, Scouting, Strategy).
    Stateless — no conversation history between calls.
    """

    def __init__(
        self,
        players: Optional[List[PlayerAsset]] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialise the agent system.

        Args:
            players: Pre-loaded, pre-valued PlayerAsset list. If None, loads
                from data/processed/player_assets_ready.csv automatically.
            api_key: Anthropic API key. If None, reads ANTHROPIC_API_KEY env var.

        Raises:
            ValueError: If no API key is found.
            FileNotFoundError: If players=None and the CSV does not exist.
        """
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key= to AgentSystem()."
            )

        self._players = players if players is not None else _load_players_from_csv(_CSV_PATH)

        client = anthropic.Anthropic(api_key=resolved_key)
        self._coordinator = CoordinatorAgent(client=client)
        self._agents = {
            "contract": ContractAgent(client=client),
            "scouting":  ScoutingAgent(client=client),
            "strategy":  StrategyAgent(client=client),
        }

    def ask(self, query: str) -> Dict[str, object]:
        """Answer a natural language NFL roster question.

        Routes to the most appropriate specialist agent and returns a
        structured response grounded in real player data.

        Args:
            query: Natural language question about the NFL roster.

        Returns:
            Dict with keys:
                query (str): the original question
                agent (str): which specialist answered, or 'error'
                response (str): Claude's natural language answer
                data_used (List[str]): player/team names injected as context
        """
        try:
            category = self._coordinator.route(query)
            agent = self._agents[category]
            return agent.run(query, self._players)
        except anthropic.APIError as exc:
            logger.warning("API error in AgentSystem.ask: %s", exc)
            return {
                "query": query,
                "agent": "error",
                "response": f"Agent encountered an error: {exc}",
                "data_used": [],
            }


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    system = AgentSystem()  # loads from CSV, reads ANTHROPIC_API_KEY

    sample_queries = [
        ("contract",  "Who are the most undervalued players on the 49ers?"),
        ("scouting",  "Generate a scouting report on Brock Purdy"),
        ("strategy",  "How does our cap allocation compare to Super Bowl winners?"),
    ]

    for expected_agent, query in sample_queries:
        logger.info("\n" + "=" * 60)
        logger.info("Query: %s", query)
        result = system.ask(query)
        logger.info("Agent: %s", result["agent"])
        logger.info("Data used: %s", result["data_used"][:5])
        logger.info("Response:\n%s", result["response"])
```

- [ ] **Step 4: Run all AgentSystem tests — expect all to pass**

```bash
conda run -n nfl_analytics pytest tests/test_agent_system.py -v
```
Expected: all tests pass (coordinator + contract + scouting + strategy + AgentSystem = ~28 tests).

- [ ] **Step 5: Run the full suite to check no regressions**

```bash
conda run -n nfl_analytics pytest tests/ -q 2>&1 | tail -5
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/agents/agent_system.py tests/test_agent_system.py
git commit -m "feat: add AgentSystem entry point (Priority 4 complete)"
```

---

## Self-Review

**Spec coverage:**
- Architecture (coordinator routes, 2 API calls, stateless) ✓ Task 1
- `AgentSystem.__init__` (players=None → CSV, api_key → env var, ValueError) ✓ Task 5
- `AgentSystem.ask()` return dict (query, agent, response, data_used) ✓ Task 5
- `CoordinatorAgent.route()` (LLM classification, fallback to scouting) ✓ Task 1
- `ContractAgent` (financial table, 30-player cap, SF first, data_used = names) ✓ Task 2
- `ScoutingAgent` (performance table, name-match prioritisation, 30-player cap) ✓ Task 3
- `StrategyAgent` (DivisionAnalyzer, team-level context, data_used = team names) ✓ Task 4
- One shared `anthropic.Anthropic` client, passed to all agents ✓ Task 5
- All 8 test scenarios (ValueError, CSV load, routing, fallback, keys, strings, API error, e2e) ✓ Task 5
- Error handling table (all 6 rows) ✓ Tasks 1 + 5
- `if __name__ == "__main__"` demo block ✓ Task 5
- `anthropic` added to requirements.txt ✓ Task 1
- No `print()`, logging at DEBUG for injected data ✓ All tasks
- Absolute imports ✓ All tasks
- Google-style docstrings ✓ All tasks

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:**
- `ContractAgent.run()` → `Dict[str, object]` ✓ (matches spec and AgentSystem return type)
- `ScoutingAgent.run()` → `Dict[str, object]` ✓
- `StrategyAgent.run()` → `Dict[str, object]` ✓
- `CoordinatorAgent.route()` → `str` ✓
- `AgentSystem.ask()` → `Dict[str, object]` ✓
- `data_used` is always `List[str]` ✓ (player names for contract/scouting, team names for strategy)
