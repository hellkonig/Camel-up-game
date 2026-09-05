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

## Completed Foundation Step: CI Baseline

Status: `Done`

Goal: Add a GitHub Actions workflow before larger refactors so every pull
request has the same quality gate as local development.

Tasks:

- [x] Create `.github/workflows/ci.yml`.
- [x] Run CI on pull requests and pushes to `main`.
- [x] Install dependencies with `uv sync --extra dev`.
- [x] Run the documented checks:

```bash
uv run python -m pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m mypy
```

Acceptance criteria:

- A pull request shows automated CI status on GitHub.
- The CI workflow runs the same commands documented in `README.md` and
  `AGENTS.md`.
- The workflow is CI only; no deployment or release automation is needed yet.

## Phase 1: Engine And Package Foundation (Immediate Sequence)

Status: `Doing`

Goal: Move from prototype root modules to a clean `src/` package layout and
establish stable state, rule, action, and turn boundaries before migrating
consumers. `engine` represents the deterministic Camel Up game engine: state,
rules, legal actions, scoring, and turn progression. It should not become a
flat bucket for unrelated shared code.

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

- `engine.state`: Immutable domain dataclasses and state containers such as
  `CamelPosition`, `BoardState`, `GameState`, `DieRoll`, `SpectatorTile`, and
  player state.
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

- [x] Create `src/camel_up/engine` with semantic modules rather than one large
      `board.py` or `rules.py`.
- [x] Replace the mutable `Camel` and `Board` state model with canonical engine
      coordinates, retaining prototype adapters only while the CLI needs them.
- [x] Introduce `GameState` before adding more rule behavior.
- [x] Put movement rules in `engine.movement`, dice rules in `engine.dice`,
      tile rules in `engine.tiles`, betting rules in `engine.betting`, and
      scoring rules in `engine.scoring`.
- [x] Re-export only stable public functions and dataclasses from
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

### Recommended Pull Request Sequence

Implement the engine in dependency order so later pull requests consume stable
state and rule APIs instead of redesigning them. Each pull request should be
based on the merged pull request before it, keep the CLI runnable, and pass all
documented checks.

Target 200-400 changed lines of active implementation and tests per pull
request. Documentation and isolated legacy compatibility adapters do not count
toward that target. Split a pull request at a semantic module boundary if it
would exceed the target; do not change the dependency order to preserve a PR
number.

#### PR 1: `refactor: add engine state foundation`

Status: `Done`

Suggested branch: `chore/engine-state-foundation`

Goal: Establish the engine package and typed state model without changing game
behavior.

Tasks:

- [x] Create `src/camel_up/engine/__init__.py` and
      `src/camel_up/engine/state.py`. Add other semantic modules only when they
      gain real responsibilities.
- [x] Represent camel placement once through immutable, typed coordinates in
      `engine.state`; derive board stacks rather than storing both forms.
- [x] Introduce a typed `GameState` foundation that owns the board and leg dice
      inventory. Add player and betting state in focused follow-up pull
      requests.
- [x] Document stack ordering and state mutation expectations in docstrings and
      tests.
- [x] Re-export only the state types intended for use outside `engine.state`.
- [x] Keep `components.py` as a temporary compatibility shim backed by an
      isolated prototype adapter; do not expose mutable adapters from
      `camel_up.engine`.
- [x] Update tests to import state types through `camel_up.engine`.

Setup-state contract:

- `GameState.pre_setup()` contains seven unplaced camels.
- The deterministic setup transition introduced with dice rules will calculate
  all starting positions and then construct one complete `BoardState`.
- Individual setup rolls may be emitted as replay or UI events, but they are not
  player decision points or intermediate engine states for agents and search.

Acceptance criteria:

- [x] Existing construction and board-placement behavior is preserved through the
  temporary CLI adapter.
- [x] `GameState` provides an explicit home for state currently held in module
  globals.
- [x] Engine states are immutable and hashable for safe branching and
  transposition-table use.
- [x] `uv run camel-up` and all documented checks still pass.

Review focus:

- State ownership, dataclass invariants, type design, and compatibility with the
  prototype.

#### PR 2: `refactor: add deterministic dice and atomic setup`

Status: `Done`

Suggested branch: `chore/deterministic-dice-setup`

Goal: Establish deterministic dice transitions and commit initial camel
placement as one complete state change.

Tasks:

- [x] Add `engine.dice` for dice inventory, die selection, grey die face
      generation, and leg dice reset.
- [x] Pass or store a seeded `random.Random` instance instead of using global
      random functions.
- [x] Add an immutable `DieRoll` result that records the selected die, camel,
      and distance without storing the random generator in `GameState`.
- [x] Emit unambiguous immutable setup rolls that distinguish the grey die's
      printed camel from the crazy camel chosen for placement.
- [x] Add an atomic seeded setup transition that calculates all starting camel
      positions before constructing the next `GameState`.
- [x] Keep engine functions free of terminal input and output.
- [x] Add deterministic dice tests that compare repeated rolls from the same
      seed, including grey die behavior.
- [x] Retain compatibility wrappers only where the CLI still needs them.

Acceptance criteria:

- [x] The same seed and dice state produce the same sequence of rolls.
- [x] Initial setup returns either the unchanged pre-setup state on failure or
      one state containing all seven placed camels; it never exposes partial
      setup.
- [x] Dice removal and leg reset preserve canonical dice ordering.
- [x] All documented checks pass.

Review focus:

- Randomness injection, state ownership, grey die behavior, setup ordering, and
  atomicity.

Non-goals:

- Camel movement after setup, spectator tile effects, player state, betting,
  scoring, legal actions, turns, CLI migration, agents, and RL environments.

#### PR 3: `refactor: add immutable stack movement rules`

Status: `Done`

Suggested branch: `chore/immutable-stack-movement`

Goal: Move camel movement behind deterministic, immutable engine functions
using the stable state and dice results from PR 2.

Tasks:

- [x] Add `engine.movement` for selecting a camel and every camel above it,
      placing stacks, updating positions, racing-camel forward movement,
      crazy-camel backward movement, and finish-line handling.
- [x] Resolve a grey die's printed camel to the moving crazy camel, including
      the passenger and stacked-crazy-camel overrides.
- [x] Place normally moving camel units above the destination stack; defer the
      under-stack rule for booing spectator tiles to the tile-rules PR.
- [x] Keep movement functions free of random selection, reject terminal input,
      and mark finish crossing terminal in the returned state.
- [x] Add concrete movement tests for stack ordering, moving a camel with
      camels above it, both grey-die exceptions, crazy-camel backward movement,
      and exact or overshooting finish-line crossings.

Acceptance criteria:

- Moving a camel preserves the order of the carried stack.
- Crazy camel backward movement and grey-die overrides are explicitly
  tested.
- Source and destination stack levels remain contiguous after every move.
- All documented checks pass.

Review focus:

- Forward and backward placement, carried-stack semantics, finish-line
  boundaries, and immutable board replacement.

Non-goals:

- Spectator tile effects, player state, betting, scoring, legal actions, turns,
  CLI migration, agents, and RL environments.

#### PR 4: `feat: add player state foundation`

Status: `Done`

Suggested branch: `feat/player-state-foundation`

Goal: Add canonical player-owned state before betting, turn, CLI, agent, or RL
code begins consuming `GameState`.

Tasks:

- [x] Add an immutable, hashable `PlayerState` and store players in
      `GameState.players` using canonical `player_id` order.
- [x] Enforce the supported three-to-eight-player range and have
      `GameState.pre_setup()` create the canonical player tuple, defaulting to
      three players.
- [x] Define the relationship between `current_player` and the canonical player
      tuple, including constructor validation.
- [x] Represent money, pyramid-ticket counts, held leg-betting tickets, and
      available finish cards without adding rule transitions yet.
- [x] Keep spectator-tile coordinates in `BoardState`; derive whether a
      player's tile is placed instead of duplicating that fact in `PlayerState`.
- [x] Document `GameState` as authoritative engine truth and defer
      player-relative hidden-information masking to future observation encoders.
- [x] Add tests for canonical ordering, invalid ownership, immutable updates,
      equality, and hashing.

Acceptance criteria:

- All player-owned information introduced in this PR has one authoritative
  location in `GameState`.
- Equivalent player states compare and hash identically for MCTS transpositions.
- Player state contains data only; shared betting supplies, ordered final-bet
  records, betting behavior, scoring, and turns remain in later rule modules.
- All documented checks pass.

Review focus:

- State ownership, canonical ordering, avoiding duplicated facts, and future
  observation encoding.

The original betting-and-scoring pull request crossed three independently
reviewable rule boundaries and was likely to exceed the target size. Implement
it as PRs 5a through 5c so state ownership stabilizes before either settlement
path consumes it.

Rule contract for this sequence:

- Use the [Camel Up Second Edition rulebook][camel-up-second-edition-rules] as
  the source of truth for base-game betting and settlement behavior.
- Implement the Camel Up Second Edition base-game supplies and payouts. Each
  racing camel begins a leg with betting tickets worth 5, 3, 2, and 2, in that
  take order.
- Rank racing camels by track progress and stack level; a racing camel higher
  in a stack is ahead. A racing camel carried across the backward finish line
  by a crazy camel is least advanced.
- A leg ticket pays its printed value for first place, 1 Egyptian Pound for
  second place, and loses 1 Egyptian Pound otherwise. Each pyramid ticket pays
  1 Egyptian Pound.
- Correct final bets, considered in their placement order without incorrect
  bets consuming a payout position, pay 8, 5, 3, and 2 Egyptian Pounds; every
  later correct bet pays 1. Each incorrect final bet loses 1.
- A player's balance never falls below zero.

[camel-up-second-edition-rules]: https://www.lookout-spiele.de/upload/en_camelup.html_CamelUp_PZE30070_Rules_EN_WEB_240305.pdf

#### PR 5a: `feat: add betting state and placement rules`

Status: `Done`

Suggested branch: `feat/betting-rules`

Goal: Represent shared betting state and support deterministic, immutable bet
placement without implementing settlement.

Tasks:

- [x] Add canonical shared leg-ticket supplies and separate ordered final
      winner and loser bet records to `GameState`.
- [x] Keep held leg tickets and unused finish cards in `PlayerState`; do not
      duplicate player-owned data in shared state.
- [x] Add `engine.betting` functions that take a leg ticket or place a finish
      card into the requested final-bet record.
- [x] Validate player identity, racing-camel identity, ticket availability, and
      finish-card availability while leaving current-turn enforcement to the
      future action layer.
- [x] Preserve canonical ordering and hashability across all betting state.
- [x] Add focused tests for ticket take order and exhaustion, final-bet order,
      unavailable finish cards, invalid input, and immutable replacement.

Acceptance criteria:

- Every ticket and finish card has one authoritative location in a state.
- Replaying the same ordered bet placements produces equal, hash-equivalent
  states and final-bet records.
- Bet placement contains no scoring, turn advancement, or CLI behavior.
- All documented checks pass.

Review focus:

- Public versus player-owned state, canonical ordering, validation boundaries,
  and immutable ownership transfer.

Non-goals:

- Camel ranking, payouts, leg resets, legal actions, turns, CLI migration,
  agents, and RL environments.

#### PR 5b: `feat: add leg ranking and settlement`

Status: `Done`

Suggested branch: `feat/leg-scoring`

Goal: Score one leg deterministically using the stable board, player, and
betting state from PR 5a.

Tasks:

- [x] Add `engine.scoring` racing-camel ordering that excludes crazy camels and
      handles shared stacks and both finish zones.
- [x] Add immutable leg settlement for printed leg-ticket payouts, second-place
      payouts, losing-ticket penalties, and pyramid-ticket income.
- [x] Clear held leg tickets and pyramid-ticket counts and restore the canonical
      shared leg-ticket supplies after settlement.
- [x] Preserve race-long state, including money after settlement, final-bet
      records, unused finish cards, camel positions, and terminal status.
- [x] Leave dice reset, spectator-tile return, leg-number advancement, and
      current-player advancement to turn orchestration.
- [x] Add focused tests for stack-based first and second place, crazy-camel
      interactions, every payout category, zero-balance flooring, and betting
      asset reset boundaries.

Acceptance criteria:

- The same board and player holdings always produce the same ranking and
  balances.
- Leg settlement resets only betting-related leg assets.
- The scoring module has no turn, random, or CLI dependencies.
- All documented checks pass.

Review focus:

- Racing-camel ordering, payout arithmetic, non-negative balances, and the
  boundary between settlement and full leg orchestration.

Non-goals:

- Final race settlement, dice or tile reset, legal actions, turns, CLI
  migration, agents, and RL environments.

#### PR 5c: `feat: add final race settlement`

Status: `Done`

Suggested branch: `feat/final-race-scoring`

Goal: Settle ordered final winner and loser bets for a terminal race using the
ranking and betting contracts established by PRs 5a and 5b.

Tasks:

- [x] Determine the winning and losing racing camels from the canonical race
      order, including same-stack and backward-finish cases.
- [x] Score final winner and loser records independently in placement order
      using the canonical 8, 5, 3, 2, then 1 payout sequence.
- [x] Apply incorrect-bet penalties without allowing negative balances.
- [x] Record final-settlement completion in `GameState`, reject non-terminal or
      already-settled input, and preserve immutable bet history for replay and
      audit.
- [x] Add focused tests for ordered correct payouts, incorrect bets, more than
      four correct bets, same-stack winner and loser selection, backward finish,
      and deterministic balance updates.

Acceptance criteria:

- Ordered final bets and resulting balances are reproducible from the same
  terminal state.
- Winner and loser bets use one shared ranking contract and cannot disagree
  about race order.
- Final settlement cannot credit the same terminal state more than once.
- Final settlement contains no turn or CLI behavior.
- All documented checks pass.

Review focus:

- Terminal-state validation, ordered payout correctness, winner and loser
  selection, and non-negative balances.

Non-goals:

- Action generation, turn orchestration, CLI migration, agents, and RL
  environments.

The original legal-actions-and-turn-progression pull request crosses three
stable rule boundaries. Implement it as PRs 6a through 6c so spectator-tile
semantics stabilize before action indexing, and action indexing stabilizes
before turn orchestration consumes it.

#### PR 6a: `feat: add spectator tile rules`

Status: `Done`

Suggested branch: `feat/spectator-tile-rules`

Goal: Complete deterministic spectator-tile placement, rewards, movement
effects, and leg-boundary return transitions.

Tasks:

- [x] Add `engine.tiles` for immutable tile placement and replacement.
- [x] Apply cheering and booing movement effects while preserving carried-stack
      order and the booing tile's under-stack rule.
- [x] Reverse tile displacement for crazy camels and credit the tile owner 1 EP.
- [x] Keep a triggered tile on its space until the leg-boundary return
      transition.
- [x] Add focused tests for placement constraints, both movement effects, crazy
      camels, stack ordering, owner rewards, finish crossings, and tile return.

Acceptance criteria:

- Tile placement and movement are immutable and deterministic.
- A tile-triggered move preserves complete camel-unit ordering and valid stack
  levels, including when a booing tile returns a unit to its source space.
- Tile rules do not enforce current-player turns or perform full leg
  orchestration.
- All documented checks pass.

Non-goals:

- Typed actions, legal-action masks, turn progression, emitted events, CLI
  migration, agents, and RL environments.

#### PR 6b: `feat: add legal actions and masks`

Suggested branch: `feat/legal-actions-masks`

Goal: Define typed player choices and stable legal-action indices without
applying turns.

Tasks:

- [ ] Add typed actions for rolling, spectator tiles, leg bets, and final bets.
- [ ] Add `engine.actions` for legal action generation and stable legal action
      masks.
- [ ] Add tests for illegal choices and action-mask agreement.

Acceptance criteria:

- `get_legal_actions` and the legal action mask describe the same choices.
- Equivalent states expose identical ordered actions and masks.
- Action queries do not mutate state or advance turns.

#### PR 6c: `feat: add deterministic turn progression`

Suggested branch: `feat/turn-progression`

Goal: Compose the completed rules from PR 5c behind one deterministic action
and turn interface for all future consumers.

Tasks:

- [ ] Add `engine.turn` for `apply_action`, current-player advancement, leg
      completion, game termination, and emitted events.
- [ ] Keep action application atomic and expose no partially updated states.
- [ ] Add tests for action application, leg boundaries, replay determinism, and
      terminal transitions.

Acceptance criteria:

- Replaying the same seed and action sequence produces the same states and
  events.
- CLI, search, and RL code can share one action application API.
- All documented checks pass.

Review focus:

- Legal-action completeness, stable action indices, turn boundaries, event
  design, and deterministic composition of rule modules.

#### PR 7: `refactor: migrate CLI to engine API`

Suggested branch: `chore/engine-cli-cutover`

Goal: Complete the package cutover so the CLI is a thin consumer of engine
behavior and production code is covered by project tooling.

Tasks:

- [ ] Add the smallest public engine façade needed by the CLI.
- [ ] Move gameplay orchestration out of root-level `main.py`.
- [ ] Move rendering, prompts, and printing into `camel_up.cli`.
- [ ] Replace the CLI's `runpy` bridge with direct calls to engine APIs.
- [ ] Add or update CLI smoke tests and verify `uv run camel-up` still starts.
- [ ] Remove `components.py`, root-level `main.py`, and
      `py-modules = ["components", "main"]` after all imports have migrated.
- [x] Configure Ruff to check `src` and `tests`.
- [x] Configure MyPy to check `src/camel_up` and `tests` with incremental
      strictness.
- [ ] Update this plan and README examples to reflect the final package paths.

Acceptance criteria:

- CLI code does not implement or duplicate dice or movement rules.
- Engine modules contain no `print()`, `input()`, or CLI rendering.
- Tests and application code import through `camel_up`, not root modules.
- The CLI and all documented checks pass without compatibility shims.

Review focus:

- Package boundaries, public API size, CLI behavior, and removal of legacy
  imports.

RL observation encoding, environment wrappers, agents, and training code remain
outside this sequence. Add them only after PR 6 stabilizes the state, action,
event, and legal-action-mask contracts. PR 7 is deliberately the first consumer
migration so it does not need to be rewritten around incomplete engine APIs.

## Phase 2: Tooling Baseline

Status: `Done`

Goal: Make formatting, linting, type checking, and tests cover production code.

Tasks:

- [x] Configure Ruff to check `src` and `tests`.
- [x] Configure MyPy to check `src/camel_up` and `tests`.
- [x] Keep strictness incremental so refactors remain manageable.
- [x] Ensure all documented commands work:

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

Status: `Doing`

Goal: Replace global, interactive, random behavior with explicit deterministic
game state and rule APIs.

Tasks:

- [x] Represent engine state with dataclasses such as `CamelPosition`,
      `BoardState`, `GameState`, `DieRoll`, `SpectatorTile`, and player state.
- [x] Inject or store `random.Random` instead of using global `random`.
- [x] Remove printing and user input from engine logic.
- [x] Make dice rolling deterministic under a fixed seed.
- [x] Preserve camel stack ordering semantics.
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

Status: `Doing`

Goal: Build confidence around high-risk game rules with focused tests.

High-priority areas:

- [x] Camel stack ordering.
- [x] Moving a camel with camels above it.
- [x] Crazy camel backward movement.
- [x] Grey die behavior.
- [x] Spectator tile placement constraints.
- [x] Spectator tile movement effects.
- [ ] Leg reset behavior.
- [x] End-of-game detection.
- [x] Winner and runner-up ordering.
- [ ] Legal actions and legal action masks.
- [x] Determinism with fixed seeds.

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

Status: `Doing`

Goal: Make quality checks automatic and standardize contribution flow.

Tasks:

- [x] Add GitHub Actions for tests, Ruff, formatting, and MyPy.
- [ ] Add or update `CONTRIBUTING.md`.
- [x] Keep README setup and command instructions current.
- [ ] Add architecture notes once the engine API stabilizes.
- [ ] Ensure `.gitignore` excludes virtualenvs, caches, checkpoints, datasets,
      and generated outputs.

Acceptance criteria:

- Every pull request can be checked automatically.
- New contributors can install, run, test, and understand the project layout.

## First Milestone

The recommended first milestone is intentionally small and starts with CI:

- [x] Add `.github/workflows/ci.yml`.
- [x] Verify the current documented checks pass in CI.
- [x] Create `src/camel_up/engine`.
- [x] Add canonical `CamelPosition`, `BoardState`, and `GameState` types while
      isolating the temporary mutable CLI adapter.
- [ ] Update imports and CLI.
- [x] Expand Ruff and MyPy to check `src`.
- [x] Add focused tests for stack movement.
- [x] Add focused tests for deterministic dice rolling and atomic setup.

This milestone establishes the package foundation without attempting to
redesign the full game in one pass. Complete the remaining work through the
dependency-ordered pull requests described in Phase 1.
