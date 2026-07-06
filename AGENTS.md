# AGENTS.md - Camel Up Game

## Project Overview

This repository is a Python prototype of the Camel Up board game. The long-term
goal is to turn it into a reliable game engine and training environment for AI
agents.

The current codebase is intentionally small and not yet production quality:

- `components.py` contains mutable `Board` and `Camel` classes.
- `main.py` contains the executable game loop and console visualization.
- There is no package structure, test suite, dependency file, formatter, type
  checker, or ML environment yet.

When changing this repo, prioritize correctness, determinism, and testability
before adding ML training code.

## Current Commands

```bash
uv run python main.py
```

Install development dependencies:

```bash
uv sync --extra dev
```

Run checks:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m mypy
```

The initial lint and type-check configuration covers the test baseline. Expand
the checked source paths as the legacy prototype code is refactored into the
future package structure.

## Intended Direction

The preferred architecture is to separate the project into these concerns over
time:

```text
camel_up/
  core/       # Game state, rules, movement, scoring, legal actions
  agents/     # Random, heuristic, Monte Carlo, and learning agents
  envs/       # Gymnasium-style RL environment wrappers
  cli/        # Human-playable command-line interface
tests/
```

Do not mix these concerns in new code. In particular:

- Core game logic should not call `print()` or `input()`.
- Randomness should be injectable or seedable.
- ML code should depend on a stable game engine API, not on CLI behavior.
- Agent code should use legal-action APIs rather than duplicating rule logic.

## Engineering Conventions

- Use Python 3 type hints for new or substantially edited code.
- Prefer dataclasses or small explicit classes for game state.
- Use `snake_case` for functions and variables, `PascalCase` for classes.
- Keep functions small and rule-focused.
- Avoid hidden global state.
- Avoid in-place mutation unless it is contained inside a clear engine method.
- Use explicit domain names such as `camel_color`, `space_index`, `stack_index`,
  `leg_dice`, and `spectator_tiles`.
- Keep comments concise and only where they clarify non-obvious game rules.

## Game Engine Standards

Game logic must be deterministic when given the same seed and action sequence.

When implementing or refactoring rules:

- Add or update tests for the behavior.
- Preserve stack ordering semantics.
- Treat crazy camels, grey die behavior, spectator tiles, leg resets, and game
  end conditions as high-risk rule areas.
- Prefer returning structured results over printing messages.
- Validate illegal actions with clear exceptions or legal-action masks.

Known current issues to keep in mind:

- `main.py` helper functions depend on globals such as `board`, `camels`, and
  `crazy_camel_set`.
- `components.py` uses global `random` directly.
- `place_spectator_tile()` refers to `self.block`, which does not exist.
- The crazy-camel-alone check in `main.py` has incorrect boolean logic.
- There are no tests protecting current behavior.

## ML Engineering Standards

Do not start training work until the core rules are testable and deterministic.

For future ML work:

- Prefer a Gymnasium-compatible environment API.
- Expose legal action masks.
- Separate observation encoding from game state.
- Keep reward calculation explicit and documented.
- Track seeds, config, checkpoints, and evaluation results.
- Start with random and heuristic baselines before reinforcement learning.
- Evaluate agents against fixed seeds and fixed opponent policies.

## Testing Expectations

When tests are introduced, cover at least:

- Initial camel placement.
- Dice availability and leg reset.
- Camel stack movement.
- Crazy camel movement.
- Spectator tile placement constraints.
- Winner detection.
- Deterministic replay with a fixed seed.
- Legal action generation for agents.

Run the relevant tests before finishing changes. If tests or tooling do not yet
exist, say that explicitly in the final response.

## Dependency Policy

- Avoid adding dependencies for simple core game logic.
- Ask before adding ML-heavy dependencies such as PyTorch, Gymnasium,
  Stable-Baselines3, Ray/RLlib, Weights & Biases, or MLflow.
- If a dependency is added, add proper project metadata first, preferably through
  `pyproject.toml`.

## Git And Generated Files

- Use branch names in the form `feat/<name>`, `fix/<name>`, or
  `chore/<name>`.
- Use commit messages in the form `<type>: <description>`, for example
  `feat: add legal action API`.
- Use PR titles in the same form as commit messages, for example
  `chore: set up project tooling`.
- Do not commit secrets, local `.env` files, checkpoints, datasets, or large
  generated experiment outputs.
- Do not edit `__pycache__` or other generated Python artifacts.
- Keep commits focused: rule changes, tooling changes, and ML experiments should
  be separate where practical.

## Agent Workflow

Before making code changes:

- Inspect the current files rather than assuming the future package structure
  already exists.
- Keep edits scoped to the user's request.
- Do not rewrite the whole game unless the task explicitly asks for a refactor.
- If changing game behavior, explain the rule assumption being implemented.

Before finishing:

- Run available validation commands.
- Report what was changed.
- Report any validation that could not be run because tooling is missing.
