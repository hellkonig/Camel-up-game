from dataclasses import replace

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    DieRoll,
    GameState,
    SpectatorTile,
    move_camel,
    position_of,
    stack_at,
)


def _state_with_stacks(
    stacks: dict[int, tuple[CamelId, ...]],
    *,
    open_spaces: tuple[int, ...] = (),
    spectator_tiles: tuple[SpectatorTile, ...] = (),
) -> GameState:
    positions_by_camel: dict[CamelId, CamelPosition] = {}
    for space, stack in stacks.items():
        for level, camel in enumerate(stack):
            if camel in positions_by_camel:
                raise ValueError("test stacks cannot place a camel more than once")
            positions_by_camel[camel] = CamelPosition(space=space, level=level)

    reserved_spaces = set(stacks) | set(open_spaces)
    reserved_spaces.update(tile.space for tile in spectator_tiles)
    filler_spaces = (space for space in range(16) if space not in reserved_spaces)
    for camel in CAMEL_ORDER:
        if camel not in positions_by_camel:
            positions_by_camel[camel] = CamelPosition(
                space=next(filler_spaces),
                level=0,
            )
    positions = tuple(positions_by_camel[camel] for camel in CAMEL_ORDER)
    return GameState(
        board=BoardState(
            track_length=16,
            camel_positions=positions,
            spectator_tiles=spectator_tiles,
        )
    )


def test_racing_camel_carries_upper_stack_onto_destination_stack() -> None:
    state = _state_with_stacks(
        {
            3: (CamelId.GREEN, CamelId.RED, CamelId.BLUE),
            5: (CamelId.BLACK, CamelId.PURPLE),
        }
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=2),
    )

    assert stack_at(next_state.board, 3) == (CamelId.GREEN,)
    assert stack_at(next_state.board, 5) == (
        CamelId.BLACK,
        CamelId.PURPLE,
        CamelId.RED,
        CamelId.BLUE,
    )
    assert state != next_state
    assert stack_at(state.board, 3) == (
        CamelId.GREEN,
        CamelId.RED,
        CamelId.BLUE,
    )


def test_crazy_camel_moves_backward_with_its_passengers() -> None:
    state = _state_with_stacks(
        {
            8: (CamelId.GREEN,),
            10: (CamelId.WHITE, CamelId.RED, CamelId.BLUE),
        }
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=2),
    )

    assert stack_at(next_state.board, 10) == ()
    assert stack_at(next_state.board, 8) == (
        CamelId.GREEN,
        CamelId.WHITE,
        CamelId.RED,
        CamelId.BLUE,
    )


def test_grey_die_moves_only_crazy_camel_carrying_racing_passengers() -> None:
    state = _state_with_stacks(
        {
            10: (CamelId.WHITE, CamelId.RED),
            14: (CamelId.BLACK,),
        },
        open_spaces=(9,),
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.BLACK, distance=1),
    )

    assert stack_at(next_state.board, 9) == (CamelId.WHITE, CamelId.RED)
    assert position_of(next_state.board, CamelId.BLACK) == CamelPosition(
        space=14,
        level=0,
    )


def test_grey_die_moves_upper_crazy_camel_when_they_are_directly_stacked() -> None:
    state = _state_with_stacks(
        {
            10: (CamelId.WHITE, CamelId.BLACK, CamelId.RED),
        },
        open_spaces=(9,),
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=1),
    )

    assert stack_at(next_state.board, 10) == (CamelId.WHITE,)
    assert stack_at(next_state.board, 9) == (CamelId.BLACK, CamelId.RED)


def test_grey_die_uses_printed_camel_when_no_exception_applies() -> None:
    state = _state_with_stacks(
        {
            10: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
        },
        open_spaces=(12,),
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.BLACK, distance=2),
    )

    assert position_of(next_state.board, CamelId.BLACK).space == 12
    assert position_of(next_state.board, CamelId.WHITE).space == 10


def test_grey_die_uses_printed_camel_when_both_crazy_camels_carry_racers() -> None:
    state = _state_with_stacks(
        {
            10: (CamelId.WHITE, CamelId.RED),
            14: (CamelId.BLACK, CamelId.BLUE),
        },
        open_spaces=(13,),
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.BLACK, distance=1),
    )

    assert stack_at(next_state.board, 10) == (CamelId.WHITE, CamelId.RED)
    assert stack_at(next_state.board, 13) == (CamelId.BLACK, CamelId.BLUE)


def test_forward_finish_crossing_moves_unit_to_finish_zone() -> None:
    state = _state_with_stacks(
        {
            14: (CamelId.RED, CamelId.BLUE),
        }
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=2),
    )

    assert next_state.terminal
    assert stack_at(next_state.board, 16) == (CamelId.RED, CamelId.BLUE)


def test_backward_finish_crossing_preserves_last_place_stack_order() -> None:
    state = _state_with_stacks(
        {
            1: (CamelId.WHITE, CamelId.RED, CamelId.BLUE),
            12: (CamelId.BLACK,),
        }
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=2),
    )

    assert next_state.terminal
    assert stack_at(next_state.board, -1) == (
        CamelId.WHITE,
        CamelId.RED,
        CamelId.BLUE,
    )


def test_crazy_camel_crossing_finish_alone_still_ends_game() -> None:
    state = _state_with_stacks(
        {
            0: (CamelId.WHITE,),
        }
    )

    next_state = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=1),
    )

    assert next_state.terminal
    assert stack_at(next_state.board, -1) == (CamelId.WHITE,)


def test_movement_rejects_incomplete_or_terminal_game() -> None:
    roll = DieRoll(die=DieId.RED, camel=CamelId.RED, distance=1)
    with pytest.raises(ValueError, match="setup must be completed"):
        move_camel(GameState.pre_setup(), roll)

    state = _state_with_stacks({})
    with pytest.raises(ValueError, match="game has ended"):
        move_camel(replace(state, terminal=True), roll)


def test_movement_defers_spectator_tile_effects_explicitly() -> None:
    state = _state_with_stacks(
        {
            7: (CamelId.PURPLE,),
        },
        spectator_tiles=(SpectatorTile(player_id=0, space=8, effect=1),),
    )

    with pytest.raises(ValueError, match="tile movement effects"):
        move_camel(
            state,
            DieRoll(die=DieId.PURPLE, camel=CamelId.PURPLE, distance=1),
        )
