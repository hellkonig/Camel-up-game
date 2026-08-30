"""Deterministic racing-camel ranking and leg settlement rules."""

from __future__ import annotations

from dataclasses import replace

from camel_up.engine.state import (
    INITIAL_LEG_BETTING_TICKET_STACKS,
    RACING_CAMEL_ORDER,
    BoardState,
    CamelId,
    GameState,
    PlayerState,
    position_of,
)


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


def _race_progress(board: BoardState, camel: CamelId) -> tuple[int, int]:
    """Return a sortable racing progress coordinate for one placed camel."""
    position = position_of(board, camel)
    if position.space is None or position.level is None:
        raise ValueError("initial setup must be completed before ranking camels")
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


def _validate_leg_settlement(state: GameState) -> None:
    """Reject states that have not reached a scoring boundary."""
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before settling a leg")
    if not state.terminal and len(state.remaining_dice) != 1:
        raise ValueError("a leg can only be settled after five dice have been used")
