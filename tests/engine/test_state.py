from dataclasses import replace

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    MIN_PLAYERS,
    RACING_CAMEL_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    GameState,
    PlayerState,
    SpectatorTile,
    carried_camels,
    position_of,
    stack_at,
)


def _fully_placed_positions() -> tuple[CamelPosition, ...]:
    return tuple(
        CamelPosition(space=10 + index, level=0) for index in range(len(CAMEL_ORDER))
    )


def _players() -> tuple[PlayerState, ...]:
    return tuple(PlayerState(player_id=index) for index in range(MIN_PLAYERS))


def test_identifier_orders_are_stable_engine_contracts() -> None:
    expected_camel_order = (
        CamelId.RED,
        CamelId.BLUE,
        CamelId.GREEN,
        CamelId.YELLOW,
        CamelId.PURPLE,
        CamelId.WHITE,
        CamelId.BLACK,
    )
    expected_die_order = (
        DieId.RED,
        DieId.BLUE,
        DieId.GREEN,
        DieId.YELLOW,
        DieId.PURPLE,
        DieId.GREY,
    )

    assert tuple(CAMEL_ORDER) == expected_camel_order
    assert tuple(RACING_CAMEL_ORDER) == expected_camel_order[:5]
    assert tuple(DIE_ORDER) == expected_die_order


def test_pre_setup_game_has_one_unplaced_position_per_camel() -> None:
    state = GameState.pre_setup()
    expected_positions = tuple(CamelPosition() for _ in CAMEL_ORDER)

    assert state.board.track_length == 16
    assert state.board.camel_positions == expected_positions
    assert state.remaining_dice == DIE_ORDER


def test_coordinates_are_the_only_source_for_derived_stack_order() -> None:
    positions = list(_fully_placed_positions())
    positions[:4] = (
        CamelPosition(space=4, level=0),
        CamelPosition(space=4, level=2),
        CamelPosition(space=4, level=1),
        CamelPosition(space=7, level=0),
    )
    board = BoardState(track_length=17, camel_positions=tuple(positions))

    assert stack_at(board, 4) == (
        CamelId.RED,
        CamelId.GREEN,
        CamelId.BLUE,
    )
    assert position_of(board, CamelId.GREEN) == CamelPosition(space=4, level=1)
    assert carried_camels(board, CamelId.GREEN) == (
        CamelId.GREEN,
        CamelId.BLUE,
    )


def test_unplaced_camel_cannot_carry_a_stack() -> None:
    with pytest.raises(ValueError, match="must be placed"):
        carried_camels(BoardState.empty(), CamelId.RED)


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
    all_positions = list(_fully_placed_positions())
    all_positions[:2] = positions

    with pytest.raises(ValueError, match="unique and contiguous"):
        BoardState(track_length=17, camel_positions=tuple(all_positions))


def test_board_rejects_partial_camel_setup_snapshot() -> None:
    positions = list(BoardState.empty().camel_positions)
    positions[0] = CamelPosition(space=2, level=0)

    with pytest.raises(ValueError, match="either all unplaced or all placed"):
        BoardState(track_length=17, camel_positions=tuple(positions))


def test_board_rejects_missing_camel_position_entry() -> None:
    positions = BoardState.empty().camel_positions[:-1]

    with pytest.raises(ValueError, match="must contain 7 entries"):
        BoardState(track_length=17, camel_positions=positions)


def test_position_requires_both_coordinate_fields() -> None:
    with pytest.raises(ValueError, match="both be set"):
        CamelPosition(space=3)


def test_spectator_tiles_have_canonical_player_order() -> None:
    tiles = (
        SpectatorTile(player_id=1, space=5, effect=1),
        SpectatorTile(player_id=0, space=3, effect=-1),
    )

    with pytest.raises(ValueError, match="ordered by player_id"):
        BoardState(
            track_length=17,
            camel_positions=_fully_placed_positions(),
            spectator_tiles=tiles,
        )


def test_board_accepts_populated_mid_game_tile_snapshot() -> None:
    board = BoardState(
        track_length=17,
        camel_positions=_fully_placed_positions(),
        spectator_tiles=(
            SpectatorTile(player_id=0, space=3, effect=-1),
            SpectatorTile(player_id=1, space=5, effect=1),
        ),
    )

    assert [tile.space for tile in board.spectator_tiles] == [3, 5]


def test_board_rejects_spectator_tiles_sharing_a_space() -> None:
    with pytest.raises(ValueError, match="cannot share a space"):
        BoardState(
            track_length=17,
            camel_positions=_fully_placed_positions(),
            spectator_tiles=(
                SpectatorTile(player_id=0, space=3, effect=-1),
                SpectatorTile(player_id=1, space=3, effect=1),
            ),
        )


def test_board_rejects_spectator_tile_on_track_space_one() -> None:
    with pytest.raises(ValueError, match="track space 1"):
        BoardState(
            track_length=17,
            camel_positions=_fully_placed_positions(),
            spectator_tiles=(SpectatorTile(player_id=0, space=0, effect=1),),
        )


def test_board_rejects_spectator_tile_on_a_camel_space() -> None:
    with pytest.raises(ValueError, match="space with camels"):
        BoardState(
            track_length=17,
            camel_positions=_fully_placed_positions(),
            spectator_tiles=(SpectatorTile(player_id=0, space=10, effect=1),),
        )


def test_board_rejects_spectator_tiles_on_adjacent_spaces() -> None:
    with pytest.raises(ValueError, match="adjacent spaces"):
        BoardState(
            track_length=17,
            camel_positions=_fully_placed_positions(),
            spectator_tiles=(
                SpectatorTile(player_id=0, space=3, effect=-1),
                SpectatorTile(player_id=1, space=4, effect=1),
            ),
        )


def test_board_allows_spectator_tile_adjacent_to_a_camel() -> None:
    board = BoardState(
        track_length=17,
        camel_positions=_fully_placed_positions(),
        spectator_tiles=(SpectatorTile(player_id=0, space=9, effect=1),),
    )

    assert board.spectator_tiles[0].space == 9


def test_remaining_dice_use_canonical_order() -> None:
    with pytest.raises(ValueError, match="canonical order"):
        GameState(
            board=BoardState.empty(),
            players=_players(),
            remaining_dice=(DieId.BLUE, DieId.RED),
        )


def test_game_states_are_hashable_and_replaceable_without_mutation() -> None:
    state = GameState.pre_setup()
    next_state = replace(
        state,
        remaining_dice=(
            DieId.BLUE,
            DieId.GREEN,
            DieId.YELLOW,
            DieId.PURPLE,
            DieId.GREY,
        ),
    )

    transpositions = {state: "root", next_state: "child"}

    assert state.remaining_dice == DIE_ORDER
    assert transpositions[state] == "root"
    assert transpositions[next_state] == "child"


def test_finish_zone_requires_terminal_game_state() -> None:
    board = BoardState(
        track_length=16,
        camel_positions=_fully_placed_positions(),
    )

    with pytest.raises(ValueError, match="finish zone requires a terminal game"):
        GameState(board=board, players=_players())

    assert GameState(board=board, players=_players(), terminal=True).terminal


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
