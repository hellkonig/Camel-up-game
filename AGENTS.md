# AGENTS.md - Camel Up Game

## Goal

Build a reliable, deterministic Camel Up game engine with clean interfaces for
future agents and Gymnasium-style RL environments. Prioritize correctness and
testability before training code.

## Commands

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

Run a single test:

```bash
uv run python -m pytest tests/path/to/test_file.py::test_name
```

## Architecture

Use a `src/` layout as the project grows:

- `src/camel_up/core`: game state, rules, scoring, legal actions
- `src/camel_up/cli`: command-line interface
- `src/camel_up/agents`: random, heuristic, search, and learning agents
- `src/camel_up/envs`: Gymnasium-style RL wrappers

Core logic must not depend on CLI, agents, or RL environment code. CLI, agent,
and RL code must use stable core APIs rather than duplicating rules.

## Code Standards

- Follow PEP 8 and Google Python Style Guide where they do not conflict.
- Use type hints for new or substantially edited code.
- Use built-in generics such as `list[str]` and `dict[str, int]`.
- Use `X | None` instead of `Optional[X]`.
- Prefer dataclasses or small explicit classes for game state.
- Keep randomness injectable or seedable.
- Keep functions small, deterministic, and rule-focused.
- Keep comments concise and only where they clarify non-obvious game rules.

## Game And RL Rules

- Preserve camel stack ordering semantics.
- Treat crazy camels, grey die behavior, spectator tiles, leg resets, game end,
  legal actions, observation encoding, and rewards as high-risk areas.
- Add or update tests when changing rules.
- Do not add training code until core rules are deterministic and tested.
- Expose legal action masks for agents and RL environments.

## Dependencies

- Avoid dependencies for simple core game logic.
- Ask before adding ML-heavy dependencies such as PyTorch, Gymnasium,
  Stable-Baselines3, Ray/RLlib, Weights & Biases, or MLflow.
- Add dependency metadata through `pyproject.toml`.

## Git

- Branches: `feat/<name>`, `fix/<name>`, or `chore/<name>`.
- Commits and PR titles: `<type>: <description>`.
- Do not commit secrets, `.env` files, virtualenvs, caches, checkpoints,
  datasets, or large generated outputs.
- Keep commits focused.
