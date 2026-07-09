from camel_up.cli.main import main
from components import Board, Camel


def test_board_initializes_with_expected_spaces_and_dice() -> None:
    board = Board(land_len=17)

    assert len(board.blocks) == 17
    assert board.dices == ["red", "blue", "green", "yellow", "purple", "grey"]


def test_camel_can_be_constructed_with_position() -> None:
    camel = Camel(color="red", block_id=0, stack_id=0)

    assert camel.color == "red"
    assert camel.block_id == 0
    assert camel.stack_id == 0


def test_cli_entry_point_is_importable() -> None:
    assert callable(main)
