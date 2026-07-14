# Software Foundation Plan

This document tracks the work needed to turn this repository into a reliable,
modern Python project for a deterministic Camel Up game engine. The priority is
correctness and testability of the core rules before adding agents, RL
environments, or training code.

## Status Legend

- `Todo`: Not started.
- `Doing`: Currently in progress.
- `Done`: Implemented and verified.
- `Deferred`: Intentionally postponed.

## Guiding Principles

- Keep engine logic independent from CLI, agents, and RL environment code.
- Make game behavior deterministic when given the same seed or random source.
- Prefer small, explicit dataclasses and rule-focused functions.
- Add tests around rule behavior before broad feature expansion.
- Expose stable APIs that future agents and Gymnasium-style environments can
  use without duplicating game rules.
- Avoid heavyweight ML dependencies until the engine is stable.

## Phase 1: Package Structure

Status: `Todo`

Goal: Move from prototype root modules to a clean `src/` package layout with a
semantic `engine` package. `engine` represents the deterministic Camel Up game
engine: state, rules, legal actions, scoring, and turn progression. It should
not become a flat bucket for unrelated shared code.

Reference observations:

- Mature Python projects usually separate by domain responsibility once the
  package grows. Gymnasium separates environment implementations, spaces,
  wrappers, vector environments, and utilities. PettingZoo separates
  environment families and shared utilities. Pytest keeps a single internal
  package but splits implementation modules by responsibility. Python-chess is
  more compact, but still gives major concepts their own modules such as engine
  integration, PGN, variants, SVG rendering, and tablebases.
- For this project, the right shape is between python-chess and Gymnasium: a
  compact engine with semantic modules now, plus clear top-level packages for
  CLI, agents, and RL environments later.

Target structure:

```text
src/camel_up/
  engine/
    __init__.py
    api.py
    constants.py
    state.py
    dice.py
    movement.py
    tiles.py
    betting.py
    actions.py
    scoring.py
    turn.py
  cli/
    __init__.py
    main.py
  agents/
    __init__.py
  envs/
    __init__.py
tests/
  engine/
    test_dice.py
    test_movement.py
    test_tiles.py
    test_scoring.py
  cli/
```

Module responsibilities:

- `engine.state`: Domain dataclasses and state containers such as `Camel`,
  `Board`, `GameState`, `DieRoll`, `SpectatorTile`, and player state.
- `engine.dice`: Dice inventory, dice selection, grey die handling, and seeded
  roll behavior.
- `engine.movement`: Camel stack selection, placement, forward movement,
  backward movement, and finish-line handling.
- `engine.tiles`: Spectator tile placement validation and tile movement
  effects.
- `engine.betting`: Leg and race betting actions, ticket availability, and bet
  state transitions.
- `engine.scoring`: Leg scoring, race scoring, winner and runner-up ordering,
  and reward-relevant score events.
- `engine.actions`: Action types, legal action generation, and legal action
  masks.
- `engine.turn`: Turn progression, leg reset, terminal detection, and
  application of actions.
- `engine.api`: Small public façade used by CLI, agents, and RL wrappers.

Shared-code policy:

- Do not create a generic `utils` package up front.
- If code is part of game state or game rules, keep it in `engine`.
- If code is only for terminal rendering or input, keep it in `cli`.
- If code is only for action selection, keep it in `agents`.
- If code is only for Gymnasium-style wrappers, keep it in `envs`.
- Add a small `utils` or `support` module later only when the same non-engine
  helper is genuinely needed by multiple packages.

Tasks:

- [ ] Create `src/camel_up/engine` with semantic modules rather than one large
      `board.py` or `rules.py`.
- [ ] Move `Camel` and `Board` out of root-level `components.py`.
- [ ] Introduce `GameState` before adding more rule behavior.
- [ ] Put movement rules in `engine.movement`, dice rules in `engine.dice`,
      tile rules in `engine.tiles`, betting rules in `engine.betting`, and
      scoring rules in `engine.scoring`.
- [ ] Re-export only stable public functions and dataclasses from
      `camel_up.engine` or `camel_up.engine.api`.
- [ ] Move gameplay orchestration out of root-level `main.py`.
- [ ] Update CLI to call package APIs directly instead of using `runpy`.
- [ ] Remove `py-modules = ["components", "main"]` after compatibility is no
      longer needed.
- [ ] Keep imports outside the engine stable through `camel_up.engine` or
      `camel_up.engine.api`.

Acceptance criteria:

- `uv run camel-up` still runs.
- Tests import from `camel_up`, not root-level modules.
- Engine modules have clear responsibilities and no single `rules.py` grows into
  a catch-all.
- Root modules are either removed or clearly marked as temporary compatibility
  shims.

## Phase 2: Tooling Baseline

Status: `Todo`

Goal: Make formatting, linting, type checking, and tests cover production code.

Tasks:

- [ ] Configure Ruff to check `src` and `tests`.
- [ ] Configure MyPy to check `src/camel_up` and `tests`.
- [ ] Keep strictness incremental so refactors remain manageable.
- [ ] Ensure all documented commands work:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m mypy
```

Acceptance criteria:

- All checks pass locally.
- CI can run the same commands without special local setup.

## Phase 3: Deterministic Engine

Status: `Todo`

Goal: Replace global, interactive, random behavior with explicit deterministic
game state and rule APIs.

Tasks:

- [ ] Represent engine state with dataclasses such as `Camel`, `Board`,
      `GameState`, `DieRoll`, and `SpectatorTile`.
- [ ] Inject or store `random.Random` instead of using global `random`.
- [ ] Remove printing and user input from engine logic.
- [ ] Make dice rolling deterministic under a fixed seed.
- [ ] Preserve camel stack ordering semantics.
- [ ] Define clear rule functions for movement, tile effects, leg reset, and
      game end.

Candidate API shape:

```python
state = new_game(seed=123)
legal_actions = get_legal_actions(state, player_id=0)
state, events = apply_action(state, action)
```

Acceptance criteria:

- Replaying the same seed and action sequence produces the same states.
- Engine tests do not require CLI input or console output.

## Phase 4: Rule Test Coverage

Status: `Todo`

Goal: Build confidence around high-risk game rules with focused tests.

High-priority areas:

- [ ] Camel stack ordering.
- [ ] Moving a camel with camels above it.
- [ ] Crazy camel backward movement.
- [ ] Grey die behavior.
- [ ] Spectator tile placement constraints.
- [ ] Spectator tile movement effects.
- [ ] Leg reset behavior.
- [ ] End-of-game detection.
- [ ] Winner and runner-up ordering.
- [ ] Legal actions and legal action masks.
- [ ] Determinism with fixed seeds.

Acceptance criteria:

- Rule tests describe concrete board scenarios.
- A regression in stack movement, grey die behavior, or legal actions fails a
  targeted test.

## Phase 5: Stable Public Engine API

Status: `Todo`

Goal: Give CLI, agents, and RL environments a stable interface over the rules.

Candidate public functions:

```python
new_game(...)
get_legal_actions(state, player_id)
get_legal_action_mask(state, player_id)
apply_action(state, action)
is_terminal(state)
score_leg(...)
score_game(...)
encode_observation(state, player_id)
```

Tasks:

- [ ] Decide which functions are public.
- [ ] Re-export public APIs from `camel_up.engine`.
- [ ] Keep public inputs and outputs typed.
- [ ] Document state mutation expectations.

Acceptance criteria:

- CLI does not duplicate rule logic.
- Future agents can use legal actions and action masks directly.

## Phase 6: CLI Rebuild

Status: `Todo`

Goal: Make the command-line interface a thin consumer of the engine.

Tasks:

- [ ] Add a board renderer outside engine logic.
- [ ] Keep prompts and printing inside `camel_up.cli`.
- [ ] Allow a seed to be passed for reproducible CLI sessions.
- [ ] Add basic CLI smoke tests.

Acceptance criteria:

- CLI behavior uses the same engine APIs as tests and future agents.
- Engine modules remain free of `print()` and `input()`.

## Phase 7: CI And Project Hygiene

Status: `Todo`

Goal: Make quality checks automatic and standardize contribution flow.

Tasks:

- [ ] Add GitHub Actions for tests, Ruff, formatting, and MyPy.
- [ ] Add or update `CONTRIBUTING.md`.
- [ ] Keep README setup and command instructions current.
- [ ] Add architecture notes once the engine API stabilizes.
- [ ] Ensure `.gitignore` excludes virtualenvs, caches, checkpoints, datasets,
      and generated outputs.

Acceptance criteria:

- Every pull request can be checked automatically.
- New contributors can install, run, test, and understand the project layout.

## First Milestone

The recommended first milestone is intentionally small:

- [ ] Create `src/camel_up/engine`.
- [ ] Move `Camel` and `Board` into package modules.
- [ ] Update imports and CLI.
- [ ] Expand Ruff and MyPy to check `src`.
- [ ] Add focused tests for stack movement and deterministic dice rolling.

This milestone establishes the package foundation without attempting to
redesign the full game in one pass.
