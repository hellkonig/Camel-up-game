"""Deterministic, immutable betting queries and transitions."""

from __future__ import annotations

from dataclasses import replace

from camel_up.engine.state import (
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
    """Return the next available leg ticket for ``camel``, if one remains."""
    _validate_racing_camel(camel)
    return next(
        (
            ticket
            for ticket in state.available_leg_betting_tickets
            if ticket.camel is camel
        ),
        None,
    )


def take_leg_betting_ticket(
    state: GameState,
    player_id: int,
    camel: CamelId,
) -> GameState:
    """Transfer the highest available leg ticket to a player.

    This rule transition validates betting-specific availability but does not
    enforce whose turn it is. The future action layer owns turn legality.
    """
    _validate_betting_transition(state, player_id)
    ticket = available_leg_betting_ticket(state, camel)
    if ticket is None:
        raise ValueError("no leg betting ticket is available for that camel")

    ticket_index = state.available_leg_betting_tickets.index(ticket)
    available_tickets = (
        state.available_leg_betting_tickets[:ticket_index]
        + state.available_leg_betting_tickets[ticket_index + 1 :]
    )
    player = state.players[player_id]
    held_tickets = tuple(
        sorted(
            (*player.leg_betting_tickets, ticket),
            key=_leg_betting_ticket_sort_key,
        )
    )
    updated_player = replace(player, leg_betting_tickets=held_tickets)
    return replace(
        state,
        players=_replace_player(state.players, updated_player),
        available_leg_betting_tickets=available_tickets,
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
    """
    _validate_betting_transition(state, player_id)
    _validate_racing_camel(camel)
    if not isinstance(target, FinalBetTarget):
        raise ValueError("target must be winner or loser")

    player = state.players[player_id]
    if camel not in player.available_finish_cards:
        raise ValueError("that finish card is not available")

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
        raise ValueError("player_id must identify a player in players")
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before betting")
    if state.terminal:
        raise ValueError("cannot place a bet after the game has ended")
    if len(state.remaining_dice) <= 1:
        raise ValueError("the leg is complete; settle it before betting")


def _validate_racing_camel(camel: CamelId) -> None:
    """Reject crazy camels, which are never valid betting subjects."""
    if camel not in RACING_CAMEL_ORDER:
        raise ValueError("bets must predict a racing camel")


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
