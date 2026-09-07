from dataclasses import replace
from typing import Literal

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    MIN_PLAYERS,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    DieRoll,
    GameState,
    PlayerState,
    SpectatorTile,
    move_camel,
    place_spectator_tile,
    return_spectator_tiles,
    stack_at,
)


def _state_with_stacks(
    stacks: dict[int, tuple[CamelId, ...]],
    *,
    spectator_tiles: tuple[SpectatorTile, ...] = (),
    remaining_dice: tuple[DieId, ...] = DIE_ORDER,
) -> GameState:
    """Build a complete state from bottom-to-top stack definitions."""
    positions_by_camel = {
        camel: CamelPosition(space=space, level=level)
        for space, stack in stacks.items()
        for level, camel in enumerate(stack)
    }
    if set(positions_by_camel) != set(CAMEL_ORDER):
        raise ValueError("test stacks must place every camel exactly once")
    return GameState(
        board=BoardState(
            track_length=16,
            camel_positions=tuple(positions_by_camel[camel] for camel in CAMEL_ORDER),
            spectator_tiles=spectator_tiles,
        ),
        players=tuple(PlayerState(player_id=index) for index in range(MIN_PLAYERS)),
        remaining_dice=remaining_dice,
    )


def _spread_state(
    *,
    spectator_tiles: tuple[SpectatorTile, ...] = (),
    remaining_dice: tuple[DieId, ...] = DIE_ORDER,
) -> GameState:
    return _state_with_stacks(
        {
            2: (CamelId.RED,),
            7: (CamelId.BLUE,),
            6: (CamelId.GREEN,),
            8: (CamelId.YELLOW,),
            10: (CamelId.PURPLE,),
            12: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
        },
        spectator_tiles=spectator_tiles,
        remaining_dice=remaining_dice,
    )


def test_place_and_move_spectator_tile_immutably_in_canonical_order() -> None:
    state = place_spectator_tile(_spread_state(), 2, 9, -1)
    state = place_spectator_tile(state, 0, 3, 1)
    moved = place_spectator_tile(state, 2, 11, 1)

    assert moved.board.spectator_tiles == (
        SpectatorTile(player_id=0, space=3, effect=1),
        SpectatorTile(player_id=2, space=11, effect=1),
    )
    assert state.board.spectator_tiles[-1] == SpectatorTile(
        player_id=2,
        space=9,
        effect=-1,
    )


@pytest.mark.parametrize(
    ("space", "message"),
    [
        (0, "track space 1"),
        (2, "space with camels"),
        (4, "adjacent spaces"),
    ],
)
def test_tile_placement_enforces_board_constraints(
    space: int,
    message: str,
) -> None:
    state = _spread_state(
        spectator_tiles=(SpectatorTile(player_id=1, space=5, effect=1),)
    )

    with pytest.raises(ValueError, match=message):
        place_spectator_tile(state, 0, space, -1)


def test_tile_must_move_to_a_different_space() -> None:
    state = _spread_state(
        spectator_tiles=(SpectatorTile(player_id=0, space=3, effect=1),)
    )

    with pytest.raises(ValueError, match="different space"):
        place_spectator_tile(state, 0, 3, -1)


@pytest.mark.parametrize("player_id", [-1, MIN_PLAYERS])
def test_tile_placement_rejects_unknown_player(player_id: int) -> None:
    with pytest.raises(ValueError, match="must identify a player"):
        place_spectator_tile(_spread_state(), player_id, 3, 1)


def test_tile_placement_requires_an_active_setup_game() -> None:
    with pytest.raises(ValueError, match="setup must be completed"):
        place_spectator_tile(GameState.pre_setup(), 0, 3, 1)

    state = _spread_state()
    with pytest.raises(ValueError, match="game has ended"):
        place_spectator_tile(replace(state, terminal=True), 0, 3, 1)

    with pytest.raises(ValueError, match="leg is complete"):
        place_spectator_tile(
            replace(state, remaining_dice=(DieId.GREY,)),
            0,
            3,
            1,
        )


def test_cheering_tile_moves_racing_unit_forward_onto_destination_stack() -> None:
    state = _state_with_stacks(
        {
            3: (CamelId.RED, CamelId.BLUE),
            6: (CamelId.GREEN,),
            8: (CamelId.YELLOW,),
            10: (CamelId.PURPLE,),
            12: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
        },
        spectator_tiles=(SpectatorTile(player_id=1, space=5, effect=1),),
    )

    moved = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=2),
    )

    assert stack_at(moved.board, 5) == ()
    assert stack_at(moved.board, 6) == (
        CamelId.GREEN,
        CamelId.RED,
        CamelId.BLUE,
    )
    assert moved.players[1].money == 4
    assert moved.board.spectator_tiles == state.board.spectator_tiles
    assert state.players[1].money == 3


def test_booing_tile_places_racing_unit_under_destination_stack() -> None:
    state = _state_with_stacks(
        {
            3: (CamelId.GREEN, CamelId.RED, CamelId.BLUE),
            4: (CamelId.YELLOW, CamelId.PURPLE),
            10: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
        },
        spectator_tiles=(SpectatorTile(player_id=0, space=5, effect=-1),),
    )

    moved = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=2),
    )

    assert stack_at(moved.board, 3) == (CamelId.GREEN,)
    assert stack_at(moved.board, 4) == (
        CamelId.RED,
        CamelId.BLUE,
        CamelId.YELLOW,
        CamelId.PURPLE,
    )
    assert moved.players[0].money == 4


@pytest.mark.parametrize(
    ("effect", "destination"),
    [(1, 7), (-1, 9)],
)
def test_crazy_camel_reverses_tile_displacement(
    effect: Literal[-1, 1],
    destination: int,
) -> None:
    state = _state_with_stacks(
        {
            2: (CamelId.RED,),
            4: (CamelId.BLUE,),
            6: (CamelId.GREEN,),
            10: (CamelId.WHITE, CamelId.YELLOW),
            12: (CamelId.PURPLE,),
            14: (CamelId.BLACK,),
        },
        spectator_tiles=(SpectatorTile(player_id=2, space=8, effect=effect),),
    )

    moved = move_camel(
        state,
        DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=2),
    )

    assert stack_at(moved.board, destination) == (CamelId.WHITE, CamelId.YELLOW)
    assert moved.players[2].money == 4


def test_booing_tile_can_return_unit_beneath_its_source_stack() -> None:
    state = _state_with_stacks(
        {
            3: (CamelId.GREEN, CamelId.RED, CamelId.BLUE),
            6: (CamelId.YELLOW,),
            10: (CamelId.PURPLE,),
            12: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
        },
        spectator_tiles=(SpectatorTile(player_id=0, space=4, effect=-1),),
    )

    moved = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=1),
    )

    assert stack_at(moved.board, 3) == (
        CamelId.RED,
        CamelId.BLUE,
        CamelId.GREEN,
    )


def test_tile_displacement_can_end_the_game() -> None:
    state = _state_with_stacks(
        {
            2: (CamelId.BLUE,),
            4: (CamelId.GREEN,),
            6: (CamelId.YELLOW,),
            8: (CamelId.PURPLE,),
            10: (CamelId.WHITE,),
            12: (CamelId.BLACK,),
            14: (CamelId.RED,),
        },
        spectator_tiles=(SpectatorTile(player_id=0, space=15, effect=1),),
    )

    moved = move_camel(
        state,
        DieRoll(die=DieId.RED, camel=CamelId.RED, distance=1),
    )

    assert moved.terminal
    assert stack_at(moved.board, 16) == (CamelId.RED,)
    assert moved.players[0].money == 4


def test_return_spectator_tiles_only_changes_board_at_leg_boundary() -> None:
    tile = SpectatorTile(player_id=0, space=3, effect=1)
    state = _spread_state(
        spectator_tiles=(tile,),
        remaining_dice=(DieId.GREY,),
    )

    returned = return_spectator_tiles(state)

    assert returned.board.spectator_tiles == ()
    assert returned.players == state.players
    assert returned.remaining_dice == state.remaining_dice
    assert returned.leg_number == state.leg_number
    assert state.board.spectator_tiles == (tile,)
    assert return_spectator_tiles(returned) is returned


def test_return_spectator_tiles_rejects_incomplete_or_active_leg() -> None:
    with pytest.raises(ValueError, match="setup must be completed"):
        return_spectator_tiles(GameState.pre_setup())

    with pytest.raises(ValueError, match="leg boundary"):
        return_spectator_tiles(_spread_state())
