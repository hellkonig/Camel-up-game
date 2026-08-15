"""Deterministic, immutable camel stack movement rules."""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from camel_up.engine.dice import DieRoll
from camel_up.engine.state import (
    CAMEL_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    GameState,
    carried_camels,
    position_of,
    stack_at,
)

_CRAZY_CAMELS: Final = (CamelId.WHITE, CamelId.BLACK)
_RACING_CAMELS: Final = frozenset(CAMEL_ORDER[:-2])


def move_camel(state: GameState, roll: DieRoll) -> GameState:
    """Apply one physical die result to a fully set up game state.

    The selected camel carries every camel above it and the complete unit lands
    on top of any destination stack. Racing camels move clockwise; crazy
    camels move counterclockwise. Crossing either finish boundary clamps the
    unit into that boundary's finish zone and makes the game terminal.

    Dice selection and removal are handled by :func:`roll_die`; this function
    only applies the deterministic movement caused by ``roll``.

    Args:
        state: A non-terminal state with all seven camels placed.
        roll: The physical die result whose movement should be applied.

    Returns:
        A replacement state containing the moved camel unit.

    Raises:
        ValueError: If setup is incomplete, the game is terminal, or the move
            requires a spectator-tile effect that is not implemented yet.
    """
    _validate_movement_state(state)
    moving_camel = _resolve_moving_camel(state.board, roll)
    source = position_of(state.board, moving_camel)
    if source.space is None:
        raise ValueError("moving camel must be placed")

    direction = -1 if moving_camel in _CRAZY_CAMELS else 1
    raw_destination = source.space + direction * roll.distance
    destination, crossed_finish = _resolve_finish_zone(
        raw_destination,
        state.board.track_length,
    )
    if not crossed_finish and any(
        tile.space == destination for tile in state.board.spectator_tiles
    ):
        raise ValueError("spectator tile movement effects are not implemented")

    moving_unit = carried_camels(state.board, moving_camel)
    destination_level = len(stack_at(state.board, destination))
    positions = list(state.board.camel_positions)
    for level_offset, camel in enumerate(moving_unit):
        camel_index = CAMEL_ORDER.index(camel)
        positions[camel_index] = CamelPosition(
            space=destination,
            level=destination_level + level_offset,
        )

    board = replace(state.board, camel_positions=tuple(positions))
    return replace(state, board=board, terminal=crossed_finish)


def _resolve_moving_camel(board: BoardState, roll: DieRoll) -> CamelId:
    """Resolve the grey die's passenger and stacked-camel exceptions."""
    if roll.die is not DieId.GREY:
        return roll.camel

    passenger_carriers = tuple(
        camel
        for camel in _CRAZY_CAMELS
        if any(
            passenger in _RACING_CAMELS
            for passenger in carried_camels(board, camel)[1:]
        )
    )
    if len(passenger_carriers) == 1:
        return passenger_carriers[0]

    white_position = position_of(board, CamelId.WHITE)
    black_position = position_of(board, CamelId.BLACK)
    if (
        white_position.space == black_position.space
        and white_position.level is not None
        and black_position.level is not None
        and abs(white_position.level - black_position.level) == 1
    ):
        return (
            CamelId.WHITE
            if white_position.level > black_position.level
            else CamelId.BLACK
        )

    return roll.camel


def _resolve_finish_zone(destination: int, track_length: int) -> tuple[int, bool]:
    """Clamp a crossing move to the appropriate terminal finish zone."""
    if destination < 0:
        return -1, True
    if destination >= track_length:
        return track_length, True
    return destination, False


def _validate_movement_state(state: GameState) -> None:
    """Reject invalid movement inputs before constructing a replacement."""
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before moving")
    if state.terminal:
        raise ValueError("cannot move a camel after the game has ended")
