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

## Deterministic Engine Setup

Pass an explicit random source to reproduce setup and dice results. Engine
transitions return replacement states rather than mutating their inputs:

```python
import random

from camel_up.engine import GameState, roll_die, setup_game

rng = random.Random(123)
pre_setup = GameState.pre_setup()
state, setup_rolls = setup_game(pre_setup, rng)
state, roll = roll_die(state, rng)
```

`setup_game` constructs all seven camel positions atomically. Its ordered
`setup_rolls` can be used for replay or presentation without exposing partially
populated engine states. Camel movement from `roll` is implemented by the next
engine milestone.
