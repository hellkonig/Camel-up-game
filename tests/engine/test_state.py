from camel_up.engine import Board, Camel, GameState


def test_board_initializes_with_expected_spaces_and_dice() -> None:
    board = Board(land_len=17)

    assert len(board.blocks) == 17
    assert board.dices == ["red", "blue", "green", "yellow", "purple", "grey"]


def test_camel_can_be_constructed_with_position() -> None:
    camel = Camel(color="red", block_id=0, stack_id=0)

    assert camel.color == "red"
    assert camel.block_id == 0
    assert camel.stack_id == 0


def test_forward_placement_preserves_bottom_to_top_order() -> None:
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


def test_backward_placement_puts_moving_stack_under_existing_camels() -> None:
    board = Board(land_len=17)
    red = Camel("red")
    blue = Camel("blue")
    green = Camel("green")

    board.place_camel(2, [green])
    board.place_camel(2, [red, blue], forward=False)

    assert board.blocks[2] == [red, blue, green]
    assert [(camel.block_id, camel.stack_id) for camel in board.blocks[2]] == [
        (2, 0),
        (2, 1),
        (2, 2),
    ]


def test_select_camel_returns_it_and_every_camel_above() -> None:
    board = Board(land_len=17)
    red = Camel("red")
    blue = Camel("blue")
    green = Camel("green")
    board.place_camel(2, [red, blue, green])

    moving_stack = board.select_camel(blue)

    assert moving_stack == [blue, green]
    assert board.blocks[2] == [red]


def test_game_state_owns_camels_and_current_dice_inventory() -> None:
    board = Board(land_len=17)
    red = Camel("red")
    state = GameState(board=board, camels={"red": red})

    assert state.board is board
    assert state.camels == {"red": red}
    assert state.dice_inventory is board.dices

    board.toss_dice()

    assert len(state.dice_inventory) == 5

    board.one_leg_reset()

    assert state.dice_inventory is board.dices
    assert state.dice_inventory == [
        "red",
        "blue",
        "green",
        "yellow",
        "purple",
        "grey",
    ]


def test_legacy_components_module_re_exports_engine_types() -> None:
    from components import Board as LegacyBoard
    from components import Camel as LegacyCamel

    assert LegacyBoard is Board
    assert LegacyCamel is Camel
