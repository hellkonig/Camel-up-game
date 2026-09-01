from dataclasses import replace

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    MIN_PLAYERS,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    FinalBetTarget,
    GameState,
    PlayerState,
    SpectatorTile,
    place_final_bet,
    rank_racing_camels,
    settle_final_bets,
    settle_leg,
    take_leg_betting_ticket,
)


def _board_with_stacks(
    stacks: dict[int, tuple[CamelId, ...]],
    *,
    spectator_tiles: tuple[SpectatorTile, ...] = (),
) -> BoardState:
    """Build a complete board from bottom-to-top test stack definitions."""
    positions_by_camel: dict[CamelId, CamelPosition] = {}
    for space, stack in stacks.items():
        for level, camel in enumerate(stack):
            if camel in positions_by_camel:
                raise ValueError("test stacks cannot place a camel more than once")
            positions_by_camel[camel] = CamelPosition(space=space, level=level)

    if set(positions_by_camel) != set(CAMEL_ORDER):
        raise ValueError("test stacks must place every camel exactly once")
    return BoardState(
        track_length=16,
        camel_positions=tuple(positions_by_camel[camel] for camel in CAMEL_ORDER),
        spectator_tiles=spectator_tiles,
    )


def _players(player_count: int = MIN_PLAYERS) -> tuple[PlayerState, ...]:
    return tuple(PlayerState(player_id=index) for index in range(player_count))


def _active_state(
    *,
    spectator_tile: bool = False,
    player_count: int = MIN_PLAYERS,
) -> GameState:
    tiles = (SpectatorTile(player_id=2, space=3, effect=-1),) if spectator_tile else ()
    board = _board_with_stacks(
        {
            5: (CamelId.PURPLE,),
            6: (CamelId.YELLOW,),
            7: (CamelId.GREEN,),
            8: (
                CamelId.WHITE,
                CamelId.BLUE,
                CamelId.BLACK,
                CamelId.RED,
            ),
        },
        spectator_tiles=tiles,
    )
    return GameState(board=board, players=_players(player_count))


def _terminal_board() -> BoardState:
    """Return a board where red won and purple lost across finish zones."""
    return _board_with_stacks(
        {
            -1: (CamelId.BLACK, CamelId.PURPLE),
            5: (CamelId.GREEN,),
            6: (CamelId.YELLOW,),
            7: (CamelId.BLUE,),
            16: (CamelId.WHITE, CamelId.RED),
        }
    )


def test_ranking_excludes_crazy_camels_and_uses_physical_stack_level() -> None:
    board = _board_with_stacks(
        {
            6: (CamelId.PURPLE,),
            7: (CamelId.YELLOW,),
            8: (
                CamelId.BLUE,
                CamelId.WHITE,
                CamelId.RED,
                CamelId.BLACK,
                CamelId.GREEN,
            ),
        }
    )

    assert rank_racing_camels(board) == (
        CamelId.GREEN,
        CamelId.RED,
        CamelId.BLUE,
        CamelId.YELLOW,
        CamelId.PURPLE,
    )


def test_ranking_handles_forward_and_backward_finish_zone_stacks() -> None:
    board = _board_with_stacks(
        {
            -1: (  # Backward finish zone.
                CamelId.BLACK,
                CamelId.PURPLE,
                CamelId.GREEN,
            ),
            15: (CamelId.YELLOW,),
            16: (CamelId.WHITE, CamelId.RED, CamelId.BLUE),
        }
    )

    assert rank_racing_camels(board) == (
        CamelId.BLUE,
        CamelId.RED,
        CamelId.YELLOW,
        CamelId.GREEN,
        CamelId.PURPLE,
    )


def test_ranking_rejects_pre_setup_board() -> None:
    with pytest.raises(ValueError, match="setup must be completed"):
        rank_racing_camels(BoardState.empty())


def test_leg_settlement_applies_every_payout_and_resets_betting_assets() -> None:
    state = _active_state()
    for _ in range(4):
        state = take_leg_betting_ticket(state, 0, CamelId.RED)
    state = take_leg_betting_ticket(state, 0, CamelId.BLUE)
    state = take_leg_betting_ticket(state, 0, CamelId.GREEN)
    players = (
        replace(state.players[0], pyramid_ticket_count=2),
        replace(state.players[1], money=4, pyramid_ticket_count=3),
        state.players[2],
    )
    state = replace(state, players=players, remaining_dice=(DieId.GREY,))

    settled = settle_leg(state)

    # Red leads: 5 + 3 + 2 + 2. Blue is second: +1. Green loses: -1.
    # Two pyramid tickets bring player zero's total leg payout to 14 EP.
    assert tuple(player.money for player in settled.players) == (17, 7, 3)
    assert all(not player.leg_betting_tickets for player in settled.players)
    assert all(player.pyramid_ticket_count == 0 for player in settled.players)
    assert (
        settled.available_leg_betting_tickets
        == GameState.pre_setup().available_leg_betting_tickets
    )
    assert state.players[0].money == 3
    assert len(state.players[0].leg_betting_tickets) == 6


def test_leg_result_is_combined_before_money_is_floored_at_zero() -> None:
    state = take_leg_betting_ticket(_active_state(), 0, CamelId.GREEN)
    player = replace(state.players[0], money=0, pyramid_ticket_count=1)
    state = replace(
        state,
        players=(player, *state.players[1:]),
        remaining_dice=(DieId.YELLOW,),
    )

    settled = settle_leg(state)

    # The losing ticket and pyramid ticket net to zero. Flooring the loss
    # before adding the income would incorrectly leave the player with 1 EP.
    assert settled.players[0].money == 0


def test_leg_settlement_floors_a_negative_balance_at_zero() -> None:
    state = take_leg_betting_ticket(_active_state(), 0, CamelId.GREEN)
    player = replace(state.players[0], money=0)
    state = replace(
        state,
        players=(player, *state.players[1:]),
        remaining_dice=(DieId.YELLOW,),
    )

    settled = settle_leg(state)

    assert settled.players[0].money == 0


def test_repeated_leg_settlement_does_not_credit_players_again() -> None:
    state = take_leg_betting_ticket(_active_state(), 0, CamelId.RED)
    player = replace(state.players[0], pyramid_ticket_count=2)
    state = replace(
        state,
        players=(player, *state.players[1:]),
        remaining_dice=(DieId.YELLOW,),
    )

    settled = settle_leg(state)

    assert settled.players[0].money == 10
    assert settle_leg(settled) == settled


def test_leg_settlement_preserves_race_long_and_orchestration_state() -> None:
    state = take_leg_betting_ticket(_active_state(spectator_tile=True), 1, CamelId.RED)
    state = place_final_bet(
        state,
        player_id=1,
        camel=CamelId.GREEN,
        target=FinalBetTarget.WINNER,
    )
    state = replace(
        state,
        players=(
            state.players[0],
            replace(state.players[1], pyramid_ticket_count=2),
            state.players[2],
        ),
        remaining_dice=(DieId.BLUE,),
        current_player=2,
        leg_number=4,
    )

    settled = settle_leg(state)

    # Settlement changes balances and consumes leg-scoped betting assets.
    assert settled != state
    assert settled.players[1] != state.players[1]
    assert settled.available_leg_betting_tickets != state.available_leg_betting_tickets

    # It does not perform the wider leg or turn transition.
    assert settled.board == state.board
    assert settled.remaining_dice == state.remaining_dice
    assert settled.current_player == state.current_player
    assert settled.leg_number == state.leg_number
    assert settled.terminal == state.terminal
    assert settled.final_winner_bets == state.final_winner_bets
    assert settled.final_loser_bets == state.final_loser_bets
    assert tuple(player.available_finish_cards for player in settled.players) == tuple(
        player.available_finish_cards for player in state.players
    )


def test_terminal_race_can_settle_before_five_dice_have_been_used() -> None:
    state = take_leg_betting_ticket(_active_state(), 0, CamelId.RED)
    terminal_board = _board_with_stacks(
        {
            5: (CamelId.PURPLE,),
            6: (CamelId.YELLOW,),
            7: (CamelId.GREEN,),
            12: (CamelId.WHITE,),
            14: (CamelId.BLACK,),
            16: (CamelId.BLUE, CamelId.RED),
        }
    )
    state = replace(state, board=terminal_board, terminal=True)

    settled = settle_leg(state)

    assert settled.players[0].money == 8
    assert settled.remaining_dice == DIE_ORDER
    assert settled.terminal


def test_leg_settlement_rejects_pre_setup_and_unfinished_leg() -> None:
    with pytest.raises(ValueError, match="setup must be completed"):
        settle_leg(GameState.pre_setup())

    with pytest.raises(
        ValueError,
        match="non-terminal with 6 dice remaining",
    ):
        settle_leg(_active_state())


def test_final_settlement_scores_ordered_records_independently() -> None:
    state = _active_state(player_count=8)
    winner_bets = (
        (0, CamelId.BLUE),  # Incorrect bets do not consume payout positions.
        (1, CamelId.RED),
        (2, CamelId.RED),
        (3, CamelId.GREEN),
        (4, CamelId.RED),
        (5, CamelId.RED),
        (6, CamelId.RED),  # Fifth correct bet pays 1 EP.
    )
    loser_bets = (
        (0, CamelId.YELLOW),
        (2, CamelId.PURPLE),
        (1, CamelId.BLUE),
        (3, CamelId.PURPLE),
    )
    for player_id, camel in winner_bets:
        state = place_final_bet(
            state,
            player_id,
            camel,
            FinalBetTarget.WINNER,
        )
    for player_id, camel in loser_bets:
        state = place_final_bet(
            state,
            player_id,
            camel,
            FinalBetTarget.LOSER,
        )
    terminal = replace(state, board=_terminal_board(), terminal=True)

    settled = settle_final_bets(terminal)

    assert tuple(player.money for player in settled.players) == (
        1,  # Two incorrect bets: 3 - 1 - 1.
        10,  # First correct winner bet and one incorrect loser bet: 3 + 8 - 1.
        16,  # Second correct winner and first correct loser: 3 + 5 + 8.
        7,  # One incorrect winner and second correct loser: 3 - 1 + 5.
        6,
        5,
        4,
        3,
    )
    assert settled.final_bets_settled
    assert settled.final_winner_bets == terminal.final_winner_bets
    assert settled.final_loser_bets == terminal.final_loser_bets
    assert not terminal.final_bets_settled
    assert all(player.money == 3 for player in terminal.players)


def test_final_settlement_uses_stack_order_at_both_finish_zones() -> None:
    state = place_final_bet(
        _active_state(),
        player_id=0,
        camel=CamelId.BLUE,
        target=FinalBetTarget.WINNER,
    )
    state = place_final_bet(
        state,
        player_id=1,
        camel=CamelId.PURPLE,
        target=FinalBetTarget.LOSER,
    )
    terminal_board = _board_with_stacks(
        {
            -1: (CamelId.BLACK, CamelId.PURPLE, CamelId.GREEN),
            15: (CamelId.YELLOW,),
            16: (CamelId.WHITE, CamelId.RED, CamelId.BLUE),
        }
    )

    settled = settle_final_bets(replace(state, board=terminal_board, terminal=True))

    assert tuple(player.money for player in settled.players) == (11, 11, 3)


def test_final_settlement_combines_results_before_flooring_money() -> None:
    state = place_final_bet(
        _active_state(),
        player_id=0,
        camel=CamelId.BLUE,
        target=FinalBetTarget.WINNER,
    )
    state = place_final_bet(
        state,
        player_id=0,
        camel=CamelId.YELLOW,
        target=FinalBetTarget.LOSER,
    )
    players = (replace(state.players[0], money=0), *state.players[1:])

    settled = settle_final_bets(
        replace(state, board=_terminal_board(), players=players, terminal=True)
    )

    assert settled.players[0].money == 0


def test_final_settlement_rejects_invalid_or_repeated_boundaries() -> None:
    with pytest.raises(ValueError, match="before the game has ended"):
        settle_final_bets(_active_state())

    with pytest.raises(ValueError, match="setup must be completed"):
        settle_final_bets(replace(GameState.pre_setup(), terminal=True))

    settled = settle_final_bets(
        replace(_active_state(), board=_terminal_board(), terminal=True)
    )
    with pytest.raises(ValueError, match="already been settled"):
        settle_final_bets(settled)


def test_equivalent_final_settlements_are_deterministic_and_hashable() -> None:
    terminal = replace(_active_state(), board=_terminal_board(), terminal=True)

    first = settle_final_bets(terminal)
    second = settle_final_bets(terminal)

    assert first == second
    assert hash(first) == hash(second)
