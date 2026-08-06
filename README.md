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

## Implementation Order

Build stable producers before their consumers:

1. Deterministic dice, setup, and camel movement.
2. Canonical player and player-owned game state.
3. Betting and scoring rules.
4. Legal actions, action masks, and turn progression.
5. CLI migration to the stable engine API.
6. Agent and RL observation layers.

Keep each pull request focused on one semantic boundary. Target 200-400 changed
lines of active implementation and tests, excluding documentation and isolated
legacy compatibility adapters. See
[`docs/software-foundation-plan.md`](docs/software-foundation-plan.md) for the
detailed pull request sequence and acceptance criteria.
