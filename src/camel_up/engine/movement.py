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


def move_camel(state: GameState, roll: DieRoll) -> GameState:
    """Apply one physical die result to a fully set up game state.

    The selected camel carries every camel above it and the complete unit lands
    on top of any destination stack. Racing camels move forward; crazy camels
    move backward. Crossing either finish boundary clamps the unit into that
    boundary's finish zone and makes the game terminal.

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

    if moving_camel in _CRAZY_CAMELS:
        raw_destination = source.space - roll.distance
    else:
        raw_destination = source.space + roll.distance
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
    """Resolve the grey die's passenger and stacked-camel exceptions in order."""
    if roll.die is not DieId.GREY:
        return roll.camel

    only_passenger_carrier = _only_crazy_camel_with_racing_passengers(board)
    if only_passenger_carrier is not None:
        return only_passenger_carrier

    upper_crazy_camel = _upper_directly_stacked_crazy_camel(board)
    if upper_crazy_camel is not None:
        return upper_crazy_camel

    return roll.camel


def _only_crazy_camel_with_racing_passengers(
    board: BoardState,
) -> CamelId | None:
    """Return the sole crazy camel carrying racers, if there is exactly one."""
    carriers = [
        crazy_camel
        for crazy_camel in _CRAZY_CAMELS
        if _has_racing_passenger(board, crazy_camel)
    ]

    if len(carriers) != 1:
        return None
    return carriers[0]


def _has_racing_passenger(board: BoardState, crazy_camel: CamelId) -> bool:
    """Return whether a racing camel sits anywhere above ``crazy_camel``."""
    passengers = carried_camels(board, crazy_camel)[1:]
    return any(passenger not in _CRAZY_CAMELS for passenger in passengers)


def _upper_directly_stacked_crazy_camel(board: BoardState) -> CamelId | None:
    """Return the upper crazy camel when both are adjacent in one stack."""
    white_position = position_of(board, CamelId.WHITE)
    black_position = position_of(board, CamelId.BLACK)
    if white_position.space != black_position.space:
        return None
    if white_position.level is None or black_position.level is None:
        return None
    if abs(white_position.level - black_position.level) != 1:
        return None

    if white_position.level > black_position.level:
        return CamelId.WHITE
    return CamelId.BLACK


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
