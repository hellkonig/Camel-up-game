"""Deterministic, immutable betting queries and transitions."""

from __future__ import annotations

from dataclasses import replace

from camel_up.engine.state import (
    _CAMEL_INDEX,
    RACING_CAMEL_ORDER,
    CamelId,
    FinalBet,
    FinalBetTarget,
    GameState,
    LegBettingTicket,
    PlayerState,
    _leg_betting_ticket_sort_key,
)


def available_leg_betting_ticket(
    state: GameState,
    camel: CamelId,
) -> LegBettingTicket | None:
    """Return the top available leg ticket for a racing camel.

    Args:
        state: Current immutable game state.
        camel: Racing camel whose ticket stack should be queried.

    Returns:
        The top ticket, or ``None`` when that camel's stack is empty.

    Raises:
        ValueError: If ``camel`` identifies a crazy camel.
    """
    camel_index = _racing_camel_index(camel)
    ticket_stack = state.available_leg_betting_tickets[camel_index]
    return ticket_stack[-1] if ticket_stack else None


def take_leg_betting_ticket(
    state: GameState,
    player_id: int,
    camel: CamelId,
) -> GameState:
    """Transfer the highest available leg ticket to a player.

    This rule transition validates betting-specific availability but does not
    enforce whose turn it is. The future action layer owns turn legality.

    Args:
        state: Active game state before the bet.
        player_id: Stable identity of the player taking the ticket.
        camel: Racing camel backed by the requested ticket.

    Returns:
        A replacement state with the top ticket transferred to the player.

    Raises:
        ValueError: If betting is unavailable, the player or camel is invalid,
            or that camel's ticket stack is empty.
    """
    _validate_betting_transition(state, player_id)
    camel_index = _racing_camel_index(camel)
    ticket_stacks = state.available_leg_betting_tickets
    selected_stack = ticket_stacks[camel_index]
    if not selected_stack:
        raise ValueError(f"no leg betting ticket is available for {camel.value}")

    selected_ticket = selected_stack[-1]
    remaining_stack = selected_stack[:-1]
    updated_ticket_stacks = (
        *ticket_stacks[:camel_index],
        remaining_stack,
        *ticket_stacks[camel_index + 1 :],
    )
    player = state.players[player_id]
    held_tickets = tuple(
        sorted(
            (*player.leg_betting_tickets, selected_ticket),
            key=_leg_betting_ticket_sort_key,
        )
    )
    updated_player = replace(player, leg_betting_tickets=held_tickets)
    return replace(
        state,
        players=_replace_player(state.players, updated_player),
        available_leg_betting_tickets=updated_ticket_stacks,
    )


def place_final_bet(
    state: GameState,
    player_id: int,
    camel: CamelId,
    target: FinalBetTarget,
) -> GameState:
    """Move one finish card into the ordered winner or loser bet record.

    Placing a final bet does not cost money. Settlement and turn legality are
    intentionally deferred to their focused rule layers.

    Args:
        state: Active game state before the bet.
        player_id: Stable identity of the player placing the finish card.
        camel: Racing camel predicted to finish first or last.
        target: Ordered winner or loser record that receives the card.

    Returns:
        A replacement state with the card moved into the selected record.

    Raises:
        ValueError: If betting is unavailable, an argument is invalid, or the
            player has already used that camel's finish card.
    """
    _validate_betting_transition(state, player_id)
    _racing_camel_index(camel)
    if not isinstance(target, FinalBetTarget):
        raise ValueError(f"target must be winner or loser, got {target!r}")

    player = state.players[player_id]
    if camel not in player.available_finish_cards:
        raise ValueError(
            f"{camel.value} finish card is not available for player {player_id}"
        )

    available_finish_cards = tuple(
        card for card in player.available_finish_cards if card is not camel
    )
    updated_player = replace(
        player,
        available_finish_cards=available_finish_cards,
    )
    final_bet = FinalBet(player_id=player_id, camel=camel)
    winner_bets = state.final_winner_bets
    loser_bets = state.final_loser_bets
    if target is FinalBetTarget.WINNER:
        winner_bets = (*winner_bets, final_bet)
    else:
        loser_bets = (*loser_bets, final_bet)

    return replace(
        state,
        players=_replace_player(state.players, updated_player),
        final_winner_bets=winner_bets,
        final_loser_bets=loser_bets,
    )


def _validate_betting_transition(state: GameState, player_id: int) -> None:
    """Reject states and player identities that cannot place a bet."""
    if not 0 <= player_id < len(state.players):
        raise ValueError(f"player_id {player_id} must identify a player in players")
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before betting")
    if state.terminal:
        raise ValueError("cannot place a bet after the game has ended")
    if len(state.remaining_dice) <= 1:
        raise ValueError("the leg is complete; settle it before betting")


def _racing_camel_index(camel: CamelId) -> int:
    """Return a racing camel's stable supply index."""
    if not isinstance(camel, CamelId) or camel not in RACING_CAMEL_ORDER:
        raise ValueError(f"bets must predict a racing camel, got {camel!r}")
    return _CAMEL_INDEX[camel]


def _replace_player(
    players: tuple[PlayerState, ...],
    updated_player: PlayerState,
) -> tuple[PlayerState, ...]:
    """Replace one canonically indexed player without mutating the tuple."""
    return (
        players[: updated_player.player_id]
        + (updated_player,)
        + players[updated_player.player_id + 1 :]
    )
