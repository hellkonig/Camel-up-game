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


def _players() -> tuple[PlayerState, ...]:
    return tuple(PlayerState(player_id=index) for index in range(MIN_PLAYERS))


def _active_state(*, spectator_tile: bool = False) -> GameState:
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
    return GameState(board=board, players=_players())


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
            -1: (CamelId.BLACK, CamelId.PURPLE, CamelId.GREEN),
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
    assert settle_leg(settled) == settled


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

    with pytest.raises(ValueError, match="after five dice"):
        settle_leg(_active_state())
