import random
from dataclasses import replace

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    DieRoll,
    GameState,
    SetupRoll,
    position_of,
    reset_leg_dice,
    roll_die,
    setup_game,
    stack_at,
)


def _setup_state(seed: int = 1) -> GameState:
    state, _ = setup_game(GameState.pre_setup(), random.Random(seed))
    return state


def test_die_roll_rejects_mismatched_camel_or_distance() -> None:
    with pytest.raises(ValueError, match="must match"):
        DieRoll(die=DieId.RED, camel=CamelId.BLUE, distance=1)
    with pytest.raises(ValueError, match="crazy camel"):
        DieRoll(die=DieId.GREY, camel=CamelId.RED, distance=1)
    with pytest.raises(ValueError, match="1, 2, or 3"):
        DieRoll(die=DieId.BLUE, camel=CamelId.BLUE, distance=4)


def test_setup_roll_distinguishes_grey_face_from_placed_camel() -> None:
    setup_roll = SetupRoll(
        roll=DieRoll(die=DieId.GREY, camel=CamelId.BLACK, distance=2),
        placed_camel=CamelId.WHITE,
    )

    assert setup_roll.roll.camel is CamelId.BLACK
    assert setup_roll.placed_camel is CamelId.WHITE

    with pytest.raises(ValueError, match="matching camel"):
        SetupRoll(
            roll=DieRoll(die=DieId.RED, camel=CamelId.RED, distance=1),
            placed_camel=CamelId.BLUE,
        )


def test_same_seed_and_state_produce_the_same_roll_sequence() -> None:
    first_state = _setup_state()
    second_state = first_state
    first_rng = random.Random(2026)
    second_rng = random.Random(2026)
    first_rolls: list[DieRoll] = []
    second_rolls: list[DieRoll] = []

    for _ in range(5):
        first_state, first_roll = roll_die(first_state, first_rng)
        second_state, second_roll = roll_die(second_state, second_rng)
        first_rolls.append(first_roll)
        second_rolls.append(second_roll)

    assert first_rolls == second_rolls
    assert first_state == second_state
    assert len({roll.die for roll in first_rolls}) == 5
    assert len(first_state.remaining_dice) == 1


def test_roll_removes_only_the_selected_die() -> None:
    state = _setup_state()

    next_state, roll = roll_die(state, random.Random(7))

    assert roll.die not in next_state.remaining_dice
    assert next_state.remaining_dice == tuple(
        die for die in DIE_ORDER if die is not roll.die
    )
    assert state.remaining_dice == DIE_ORDER


def test_grey_die_generates_a_seeded_crazy_camel_face() -> None:
    state = replace(
        _setup_state(),
        remaining_dice=(DieId.PURPLE, DieId.GREY),
    )

    next_state, roll = roll_die(state, random.Random(0))

    assert roll == DieRoll(die=DieId.GREY, camel=CamelId.WHITE, distance=2)
    assert next_state.remaining_dice == (DieId.PURPLE,)


def test_leg_ends_with_one_unrolled_die_and_can_then_reset() -> None:
    state = _setup_state()
    rng = random.Random(9)

    for _ in range(5):
        state, _ = roll_die(state, rng)

    with pytest.raises(ValueError, match="leg is complete"):
        roll_die(state, rng)

    reset_state = reset_leg_dice(state)

    assert len(state.remaining_dice) == 1
    assert reset_state.remaining_dice == DIE_ORDER


def test_dice_cannot_reset_before_five_rolls() -> None:
    with pytest.raises(ValueError, match="after five rolls"):
        reset_leg_dice(_setup_state())

    pre_setup = replace(
        GameState.pre_setup(),
        remaining_dice=(DieId.GREY,),
    )
    with pytest.raises(ValueError, match="setup must be completed"):
        reset_leg_dice(pre_setup)

    no_dice_state = replace(_setup_state(), remaining_dice=())
    with pytest.raises(ValueError, match="after five rolls"):
        reset_leg_dice(no_dice_state)


def test_setup_is_atomic_complete_and_seeded() -> None:
    pre_setup = GameState.pre_setup()

    first_state, first_rolls = setup_game(pre_setup, random.Random(31))
    second_state, second_rolls = setup_game(pre_setup, random.Random(31))

    assert first_state == second_state
    assert first_rolls == second_rolls
    assert pre_setup.board == BoardState.empty()
    assert all(position.is_placed for position in first_state.board.camel_positions)
    assert first_state.remaining_dice == DIE_ORDER
    assert len(first_rolls) == 7
    assert {setup_roll.roll.die for setup_roll in first_rolls[:5]} == set(
        DIE_ORDER[:-1]
    )
    assert [setup_roll.roll.die for setup_roll in first_rolls[5:]] == [
        DieId.GREY,
        DieId.GREY,
    ]
    assert {setup_roll.placed_camel for setup_roll in first_rolls[5:]} == {
        CamelId.WHITE,
        CamelId.BLACK,
    }


def test_setup_rolls_define_positions_and_stack_order() -> None:
    state, rolls = setup_game(GameState.pre_setup(), random.Random(0))

    expected_stacks: dict[int, list[CamelId]] = {}
    for setup_roll in rolls:
        space = (
            state.board.track_length - setup_roll.roll.distance - 1
            if setup_roll.roll.die is DieId.GREY
            else setup_roll.roll.distance - 1
        )
        expected_stacks.setdefault(space, []).append(setup_roll.placed_camel)
        assert position_of(state.board, setup_roll.placed_camel).space == space

    for space, expected_stack in expected_stacks.items():
        assert stack_at(state.board, space) == tuple(expected_stack)

    assert rolls[5].roll.distance == rolls[6].roll.distance
    assert position_of(state.board, rolls[5].placed_camel).level == 0
    assert position_of(state.board, rolls[6].placed_camel).level == 1


def test_setup_rejection_does_not_change_state_or_rng() -> None:
    placed_state = _setup_state()
    rng = random.Random(15)
    rng_state = rng.getstate()

    with pytest.raises(ValueError, match="already been completed"):
        setup_game(placed_state, rng)

    assert placed_state == _setup_state()
    assert rng.getstate() == rng_state


def test_setup_requires_complete_dice_inventory() -> None:
    pre_setup = replace(
        GameState.pre_setup(),
        remaining_dice=(DieId.BLUE, DieId.GREEN),
    )

    with pytest.raises(ValueError, match="complete dice inventory"):
        setup_game(pre_setup, random.Random(8))


def test_roll_requires_setup_and_non_terminal_game() -> None:
    with pytest.raises(ValueError, match="setup must be completed"):
        roll_die(GameState.pre_setup(), random.Random(2))

    terminal_state = replace(_setup_state(), terminal=True)
    with pytest.raises(ValueError, match="game has ended"):
        roll_die(terminal_state, random.Random(2))


def test_setup_position_tuple_matches_canonical_camel_order() -> None:
    state, setup_rolls = setup_game(GameState.pre_setup(), random.Random(12))
    expected_positions_by_camel: dict[CamelId, CamelPosition] = {}
    expected_levels_by_space: dict[int, int] = {}
    for setup_roll in setup_rolls:
        space = (
            state.board.track_length - setup_roll.roll.distance - 1
            if setup_roll.roll.die is DieId.GREY
            else setup_roll.roll.distance - 1
        )
        level = expected_levels_by_space.get(space, 0)
        expected_positions_by_camel[setup_roll.placed_camel] = CamelPosition(
            space=space,
            level=level,
        )
        expected_levels_by_space[space] = level + 1

    assert len(expected_positions_by_camel) == len(CAMEL_ORDER)
    assert tuple(expected_positions_by_camel[camel] for camel in CAMEL_ORDER) == (
        state.board.camel_positions
    )
