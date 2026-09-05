# Camel Up Game

Deterministic Camel Up game engine with interfaces for agents and
Gymnasium-style RL environments.

## Requirements

- Python 3.10+
- `uv` for local development commands

## Development

Install development dependencies:

```bash
uv sync --extra dev
```

Run the CLI:

```bash
uv run camel-up
```

Run checks:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m mypy
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

Run pre-commit checks manually:

```bash
uv run pre-commit run --all-files
```

## Project Structure

The project uses a `src/` layout as it moves from the prototype CLI to the
deterministic engine:

- `src/camel_up/engine`: game state, rules, scoring, and legal actions
- `src/camel_up/cli`: command-line interface
- `src/camel_up/agents`: random, heuristic, search, and learning agents
- `src/camel_up/envs`: Gymnasium-style RL wrappers

Engine rules are deterministic, testable, and independent from CLI, agent, or
training code. Initial camel placement is modeled as one atomic transition from
an all-unplaced pre-setup state to a complete board; setup rolls do not create
player decision states for agents or search.

## Deterministic Engine Transitions

Pass an explicit random source to reproduce setup and dice results. Engine
transitions return replacement states rather than mutating their inputs:

```python
import random

from camel_up.engine import GameState, move_camel, roll_die, setup_game

rng = random.Random(123)
pre_setup = GameState.pre_setup()
state, setup_rolls = setup_game(pre_setup, rng)
state, roll = roll_die(state, rng)
state = move_camel(state, roll)
```

`setup_game` constructs all seven camel positions atomically. Its ordered
`setup_rolls` can be used for replay or presentation without exposing partially
populated engine states. `move_camel` then applies the physical die result as a
separate immutable transition, preserving carried-stack order, resolving the
grey die's crazy-camel exceptions, and applying spectator-tile rewards and
movement effects. Crossing either finish boundary places the moved unit in the
corresponding finish zone and returns a terminal state.

Use `place_spectator_tile` to place or move a player's cheering or booing tile.
Tile placement and movement effects are deterministic rule transitions; turn
ownership and full leg orchestration remain responsibilities of the future
action layer.

## Betting API

Use the engine betting API to take the top ticket for a racing camel or place a
finish card on the overall winner or loser record:

```python
from camel_up.engine import (
    CamelId,
    FinalBetTarget,
    place_final_bet,
    settle_final_bets,
    take_leg_betting_ticket,
)

state = take_leg_betting_ticket(state, player_id=0, camel=CamelId.RED)
state = place_final_bet(
    state,
    player_id=1,
    camel=CamelId.GREEN,
    target=FinalBetTarget.WINNER,
)

if state.terminal:
    state = settle_final_bets(state)
```

Betting transitions return a new state and leave their input unchanged. Placing
a bet does not cost money. `settle_leg` applies leg-ticket and pyramid-ticket
payouts at a scoring boundary and resets the consumed leg betting assets. Call
`settle_final_bets` on a terminal state to score the final winner and loser
records.

## Agent Compatibility

`GameState` is immutable, deterministic engine state shared by CLI, search, and
RL consumers. Future environment adapters can encode player-relative NumPy
observations and legal-action masks while hiding private opponent information.
Display names and human or agent controller selection remain outside the rule
engine, keyed by stable player IDs.
