"""Deterministic dice transitions and atomic initial camel setup."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final

from camel_up.engine.state import (
    CAMEL_ORDER,
    DIE_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    GameState,
)

_RACING_DICE: Final = DIE_ORDER[:-1]
_CRAZY_CAMELS: Final = (CamelId.WHITE, CamelId.BLACK)
_CAMEL_BY_DIE: Final = MappingProxyType(
    {
        DieId.RED: CamelId.RED,
        DieId.BLUE: CamelId.BLUE,
        DieId.GREEN: CamelId.GREEN,
        DieId.YELLOW: CamelId.YELLOW,
        DieId.PURPLE: CamelId.PURPLE,
    }
)


@dataclass(frozen=True, slots=True)
class DieRoll:
    """One physical die result before movement-specific resolution.

    For the grey die, ``camel`` is the color printed on the rolled face.
    Movement rules may later select the other crazy camel when stack rules
    require it.

    Attributes:
        die: The physical die selected from the current leg's inventory.
        camel: The matching racing camel or the crazy camel color printed on
            the grey die.
        distance: The rolled distance, from one through three spaces.
    """

    die: DieId
    camel: CamelId
    distance: int

    def __post_init__(self) -> None:
        """Require a valid camel face and a physical die distance."""
        if self.distance not in (1, 2, 3):
            raise ValueError("distance must be 1, 2, or 3")
        if self.die is DieId.GREY:
            if self.camel not in _CRAZY_CAMELS:
                raise ValueError("grey die must show a crazy camel")
        elif _CAMEL_BY_DIE.get(self.die) is not self.camel:
            raise ValueError("racing die must match its camel")


@dataclass(frozen=True, slots=True)
class SetupRoll:
    """A physical setup roll paired with the camel placed by that roll.

    During setup, the color printed on the grey die does not decide which
    crazy camel is placed. For racing dice, ``placed_camel`` matches the
    camel on ``roll``; for the grey die, it records the separately chosen
    crazy camel. Keeping both facts makes setup events replayable.

    Attributes:
        roll: The physical die result used for initial placement.
        placed_camel: The camel placed by that result.
    """

    roll: DieRoll
    placed_camel: CamelId

    def __post_init__(self) -> None:
        """Require the placement camel to match the kind of die rolled."""
        if self.roll.die is DieId.GREY:
            if self.placed_camel not in _CRAZY_CAMELS:
                raise ValueError("grey setup roll must place a crazy camel")
        elif self.placed_camel is not self.roll.camel:
            raise ValueError("racing setup roll must place its matching camel")


def roll_die(state: GameState, rng: random.Random) -> tuple[GameState, DieRoll]:
    """Roll one available die and remove it from the leg inventory.

    A Camel Up leg ends after five of the six dice have been rolled, so the
    final die remains unavailable until the caller performs a complete leg
    transition and resets the dice inventory.

    Args:
        state: A non-terminal game with completed setup and at least two dice
            remaining in the current leg.
        rng: The random source to consume for die selection and face generation.

    Returns:
        A tuple containing the replacement game state and physical die result.
    """
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before rolling")
    if state.terminal:
        raise ValueError("cannot roll dice after the game has ended")
    if len(state.remaining_dice) <= 1:
        raise ValueError("the leg is complete; reset dice before rolling again")

    die = rng.choice(state.remaining_dice)
    roll = _roll_physical_die(die, rng)
    remaining_dice = tuple(
        candidate for candidate in state.remaining_dice if candidate != die
    )
    return replace(state, remaining_dice=remaining_dice), roll


def reset_leg_dice(state: GameState) -> GameState:
    """Restore the canonical dice inventory after five rolls.

    This transition intentionally resets only dice. Turn orchestration will
    later compose it with scoring, tile returns, and leg-number advancement.

    Args:
        state: A non-terminal, fully set up game with one unrolled die left.

    Returns:
        A replacement game state with the canonical six-die inventory.
    """
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before resetting dice")
    if state.terminal:
        raise ValueError("cannot reset dice after the game has ended")
    if not state.remaining_dice:
        raise ValueError("cannot reset dice from an empty inventory")
    if len(state.remaining_dice) > 1:
        raise ValueError("dice can only be reset after five rolls")
    return replace(state, remaining_dice=DIE_ORDER)


def setup_game(
    state: GameState,
    rng: random.Random,
) -> tuple[GameState, tuple[SetupRoll, ...]]:
    """Place all seven camels in one immutable, seeded transition.

    The five racing dice are rolled in a randomized order, which resolves the
    rulebook's arbitrary ordering for camels that start on the same space. The
    grey die is then rolled once for each crazy camel. No partially populated
    ``BoardState`` is constructed or returned.

    Args:
        state: A new pre-setup game with an empty board and complete dice
            inventory.
        rng: The random source to consume for rolls, stack order, and crazy
            camel placement order.

    Returns:
        A tuple containing the fully set up game state and its ordered setup
        roll events. The events allow a caller to replay setup without exposing
        partially populated engine states.
    """
    _validate_pre_setup_state(state)
    setup_rolls = _generate_setup_rolls(rng)
    board = _build_setup_board(state.board.track_length, setup_rolls)
    return replace(state, board=board, remaining_dice=DIE_ORDER), setup_rolls


def _generate_setup_rolls(rng: random.Random) -> tuple[SetupRoll, ...]:
    """Generate ordered racing and crazy camel placement rolls."""
    racing_dice = list(_RACING_DICE)
    rng.shuffle(racing_dice)
    setup_rolls: list[SetupRoll] = []
    for die in racing_dice:
        roll = _roll_physical_die(die, rng)
        setup_rolls.append(SetupRoll(roll=roll, placed_camel=roll.camel))

    unplaced_crazy_camels = list(_CRAZY_CAMELS)
    for _ in _CRAZY_CAMELS:
        roll = _roll_physical_die(DieId.GREY, rng)
        camel = (
            rng.choice(unplaced_crazy_camels)
            if len(unplaced_crazy_camels) > 1
            else unplaced_crazy_camels[0]
        )
        unplaced_crazy_camels.remove(camel)
        setup_rolls.append(SetupRoll(roll=roll, placed_camel=camel))
    return tuple(setup_rolls)


def _build_setup_board(
    track_length: int,
    setup_rolls: tuple[SetupRoll, ...],
) -> BoardState:
    """Build one complete board from validated setup roll events."""
    spaces_by_camel: dict[CamelId, int] = {}
    stacks_by_space: dict[int, list[CamelId]] = {}
    for setup_roll in setup_rolls:
        if setup_roll.roll.die is DieId.GREY:
            space = track_length - setup_roll.roll.distance
        else:
            space = setup_roll.roll.distance - 1
        spaces_by_camel[setup_roll.placed_camel] = space
        stacks_by_space.setdefault(space, []).append(setup_roll.placed_camel)

    levels_by_camel = {
        camel: level
        for stack in stacks_by_space.values()
        for level, camel in enumerate(stack)
    }
    positions = tuple(
        CamelPosition(
            space=spaces_by_camel[camel],
            level=levels_by_camel[camel],
        )
        for camel in CAMEL_ORDER
    )
    return BoardState(
        track_length=track_length,
        camel_positions=positions,
    )


def _roll_physical_die(die: DieId, rng: random.Random) -> DieRoll:
    """Return one unresolved result from a racing or grey die.

    For the grey die, this records the printed camel color. Stack-dependent
    overrides that determine the moving crazy camel belong to movement rules.
    """
    distance = rng.randint(1, 3)
    camel = rng.choice(_CRAZY_CAMELS) if die is DieId.GREY else _CAMEL_BY_DIE[die]
    return DieRoll(die=die, camel=camel, distance=distance)


def _validate_pre_setup_state(state: GameState) -> None:
    """Reject invalid setup inputs before consuming any randomness."""
    if any(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup has already been completed")
    if state.board.spectator_tiles:
        raise ValueError("initial setup cannot contain spectator tiles")
    if state.board.track_length < 7:
        raise ValueError("track must contain at least seven spaces for setup")
    if state.remaining_dice != DIE_ORDER:
        raise ValueError("initial setup requires the complete dice inventory")
    if state.leg_number != 1 or state.terminal:
        raise ValueError("initial setup requires a new, non-terminal game")
