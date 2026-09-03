"""Deterministic racing-camel ranking and settlement rules."""

from __future__ import annotations

from dataclasses import replace

from camel_up.engine.state import (
    INITIAL_LEG_BETTING_TICKET_STACKS,
    RACING_CAMEL_ORDER,
    BoardState,
    CamelId,
    FinalBet,
    GameState,
    PlayerState,
    position_of,
)

_FINAL_BET_PAYOUTS = (8, 5, 3, 2)


def rank_racing_camels(board: BoardState) -> tuple[CamelId, ...]:
    """Return racing camels from first to last for the current board.

    Crazy camels are excluded. Racing camels farther along the track rank
    ahead, and a racing camel higher in a shared stack ranks ahead of racing
    camels below it. These rules also apply in the forward and backward finish
    zones.

    Args:
        board: Fully populated board whose racing camels should be ranked.

    Returns:
        The five racing camel identities ordered from first to last.

    Raises:
        ValueError: If initial camel placement has not been completed.
    """
    if not all(position.is_placed for position in board.camel_positions):
        raise ValueError("initial setup must be completed before ranking camels")

    return tuple(
        sorted(
            RACING_CAMEL_ORDER,
            key=lambda camel: _race_progress(board, camel),
            reverse=True,
        )
    )


def settle_leg(state: GameState) -> GameState:
    """Apply leg payouts and reset only the consumed leg betting assets.

    This is a scoring-only transition. It leaves the board and remaining dice
    unchanged and does not start the next leg.

    A regular leg can be settled after five dice have been used. A terminal
    game can be settled immediately because crossing either finish line ends
    the current leg regardless of how many dice remain.

    Ticket gains and losses plus pyramid-ticket income are combined for each
    player before applying the rule that money cannot fall below zero. The
    returned state clears held leg tickets and pyramid-ticket counts and
    restores the shared ticket supplies. Dice, spectator tiles, turn fields,
    final bets, camel positions, and terminal status are preserved for the
    future turn-orchestration layer.

    Args:
        state: Completed leg whose betting assets should be settled.

    Returns:
        A replacement state with updated balances and reset leg betting assets.

    Raises:
        ValueError: If setup is incomplete or a non-terminal leg is unfinished.
    """
    _validate_leg_settlement(state)
    first, second, *_ = rank_racing_camels(state.board)
    players = tuple(
        _settle_player(player, first=first, second=second) for player in state.players
    )
    return replace(
        state,
        players=players,
        available_leg_betting_tickets=INITIAL_LEG_BETTING_TICKET_STACKS,
    )


def settle_final_bets(state: GameState) -> GameState:
    """Apply final winner and loser bet payouts to a terminal game.

    Winner and loser records are scored independently in placement order.
    Correct bets receive 8, 5, 3, and 2 Egyptian Pounds, followed by 1 for
    every later correct bet. Incorrect bets do not consume a payout position
    and lose 1 Egyptian Pound. All of a player's final-bet results are combined
    before their balance is floored at zero.

    This scoring-only transition preserves both ordered bet records for replay
    and audit. It marks them as settled so the same terminal state cannot be
    credited twice.

    Args:
        state: Terminal game whose final betting records should be settled.

    Returns:
        A replacement state with updated balances and completed settlement.

    Raises:
        ValueError: If the game is non-terminal, setup is incomplete, or final
            bets have already been settled.
    """
    _validate_final_settlement(state)
    ranking = rank_racing_camels(state.board)
    payouts = (0,) * len(state.players)
    payouts = _score_final_bet_record(
        state.final_winner_bets,
        ranking[0],
        payouts,
    )
    payouts = _score_final_bet_record(
        state.final_loser_bets,
        ranking[-1],
        payouts,
    )

    players = tuple(
        replace(player, money=max(0, player.money + payouts[player.player_id]))
        for player in state.players
    )
    return replace(state, players=players, final_bets_settled=True)


def _race_progress(board: BoardState, camel: CamelId) -> tuple[int, int]:
    """Return a sortable racing progress coordinate for one placed camel."""
    position = position_of(board, camel)
    if position.space is None or position.level is None:
        raise ValueError(f"{camel.value} camel must be placed before ranking camels")
    return position.space, position.level


def _settle_player(
    player: PlayerState,
    *,
    first: CamelId,
    second: CamelId,
) -> PlayerState:
    """Return one player with their combined leg result applied."""
    payout = player.pyramid_ticket_count
    for ticket in player.leg_betting_tickets:
        if ticket.camel is first:
            payout += ticket.value
        elif ticket.camel is second:
            payout += 1
        else:
            payout -= 1

    return replace(
        player,
        money=max(0, player.money + payout),
        pyramid_ticket_count=0,
        leg_betting_tickets=(),
    )


def _score_final_bet_record(
    bets: tuple[FinalBet, ...],
    result: CamelId,
    payouts: tuple[int, ...],
) -> tuple[int, ...]:
    """Return payouts updated from one ordered winner or loser record."""
    updated_payouts = list(payouts)
    correct_bet_count = 0
    for bet in bets:
        if bet.camel is result:
            payout = (
                _FINAL_BET_PAYOUTS[correct_bet_count]
                if correct_bet_count < len(_FINAL_BET_PAYOUTS)
                else 1
            )
            updated_payouts[bet.player_id] += payout
            correct_bet_count += 1
        else:
            updated_payouts[bet.player_id] -= 1
    return tuple(updated_payouts)


def _validate_leg_settlement(state: GameState) -> None:
    """Reject states that have not reached a scoring boundary."""
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before settling a leg")
    if not state.terminal and len(state.remaining_dice) != 1:
        raise ValueError(
            "cannot settle an unfinished leg: state is non-terminal with "
            f"{len(state.remaining_dice)} dice remaining; expected one remaining "
            "die or a terminal game"
        )


def _validate_final_settlement(state: GameState) -> None:
    """Reject states outside the one valid final-settlement boundary."""
    if not state.terminal:
        raise ValueError("cannot settle final bets before the game has ended")
    if state.final_bets_settled:
        raise ValueError("final bets have already been settled")
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before settling final bets")
