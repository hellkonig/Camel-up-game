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

## Project Direction

The project will move toward a `src/` layout:

- `src/camel_up/core`: game state, rules, scoring, legal actions
- `src/camel_up/cli`: command-line interface
- `src/camel_up/agents`: random, heuristic, search, and learning agents
- `src/camel_up/envs`: Gymnasium-style RL wrappers

Core rules should be deterministic, testable, and independent from CLI, agent,
or training code.
