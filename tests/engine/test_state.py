from dataclasses import replace

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    BoardState,
    CamelPosition,
    GameState,
    SpectatorTile,
    carried_camels,
    position_of,
    stack_at,
)


def test_new_game_has_one_unplaced_position_per_camel() -> None:
    state = GameState()

    assert state.board.track_length == 17
    assert len(state.board.camel_positions) == len(CAMEL_ORDER)
    assert all(not position.is_placed for position in state.board.camel_positions)
    assert state.remaining_dice == DIE_ORDER


def test_coordinates_are_the_only_source_for_derived_stack_order() -> None:
    positions = (
        CamelPosition(space=4, level=0),
        CamelPosition(space=4, level=2),
        CamelPosition(space=4, level=1),
        CamelPosition(space=7, level=0),
        CamelPosition(),
        CamelPosition(space=15, level=0),
        CamelPosition(space=16, level=0),
    )
    state = GameState(board=BoardState(camel_positions=positions))

    assert stack_at(state, 4) == ("red", "green", "blue")
    assert position_of(state, "green") == CamelPosition(space=4, level=1)
    assert carried_camels(state, "green") == ("green", "blue")


def test_unplaced_camel_cannot_carry_a_stack() -> None:
    with pytest.raises(ValueError, match="must be placed"):
        carried_camels(GameState(), "red")


@pytest.mark.parametrize(
    "positions",
    [
        (
            CamelPosition(space=4, level=0),
            CamelPosition(space=4, level=0),
        ),
        (
            CamelPosition(space=4, level=0),
            CamelPosition(space=4, level=2),
        ),
    ],
)
def test_board_rejects_duplicate_or_non_contiguous_stack_levels(
    positions: tuple[CamelPosition, CamelPosition],
) -> None:
    padded_positions = positions + tuple(
        CamelPosition() for _ in range(len(CAMEL_ORDER) - len(positions))
    )

    with pytest.raises(ValueError, match="unique and contiguous"):
        BoardState(camel_positions=padded_positions)


def test_position_requires_both_coordinate_fields() -> None:
    with pytest.raises(ValueError, match="both be set"):
        CamelPosition(space=3)


def test_spectator_tiles_have_canonical_player_order() -> None:
    tiles = (
        SpectatorTile(player_id=1, space=5, effect=1),
        SpectatorTile(player_id=0, space=3, effect=-1),
    )

    with pytest.raises(ValueError, match="ordered by player_id"):
        BoardState(spectator_tiles=tiles)


def test_remaining_dice_use_canonical_order() -> None:
    with pytest.raises(ValueError, match="canonical order"):
        GameState(remaining_dice=("blue", "red"))


def test_game_states_are_hashable_and_replaceable_without_mutation() -> None:
    state = GameState()
    next_state = replace(
        state,
        remaining_dice=("blue", "green", "yellow", "purple", "grey"),
    )

    transpositions = {state: "root", next_state: "child"}

    assert state.remaining_dice == DIE_ORDER
    assert transpositions[state] == "root"
    assert transpositions[next_state] == "child"


def test_legacy_components_preserve_prototype_stack_behavior() -> None:
    from components import Board, Camel

    board = Board(land_len=17)
    red = Camel("red")
    blue = Camel("blue")
    green = Camel("green")

    board.place_camel(2, [red])
    board.place_camel(2, [blue, green])

    assert board.blocks[2] == [red, blue, green]
    assert [(camel.block_id, camel.stack_id) for camel in board.blocks[2]] == [
        (2, 0),
        (2, 1),
        (2, 2),
    ]
