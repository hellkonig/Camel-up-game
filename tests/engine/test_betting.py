import random
from dataclasses import replace
from typing import cast

import pytest

from camel_up.engine import (
    LEG_BETTING_TICKET_STACK_VALUES,
    MIN_PLAYERS,
    RACING_CAMEL_ORDER,
    CamelId,
    DieId,
    FinalBet,
    FinalBetTarget,
    GameState,
    LegBettingTicket,
    available_leg_betting_ticket,
    place_final_bet,
    setup_game,
    take_leg_betting_ticket,
)


def _setup_state(seed: int = 41) -> GameState:
    state, _ = setup_game(GameState.pre_setup(), random.Random(seed))
    return state


def _tickets_for_camel(
    state: GameState,
    camel: CamelId,
) -> tuple[LegBettingTicket, ...]:
    return state.available_leg_betting_tickets[RACING_CAMEL_ORDER.index(camel)]


def test_pre_setup_contains_canonical_bottom_to_top_ticket_stacks() -> None:
    state = GameState.pre_setup()

    for camel in RACING_CAMEL_ORDER:
        tickets = _tickets_for_camel(state, camel)

        assert tuple(ticket.value for ticket in tickets) == (
            LEG_BETTING_TICKET_STACK_VALUES
        )
        assert all(ticket.camel is camel for ticket in tickets)


def test_available_leg_betting_ticket_returns_top_ticket_or_none() -> None:
    state = _setup_state()

    assert available_leg_betting_ticket(state, CamelId.GREEN) == LegBettingTicket(
        camel=CamelId.GREEN,
        value=5,
    )

    for _ in LEG_BETTING_TICKET_STACK_VALUES:
        state = take_leg_betting_ticket(state, 0, CamelId.GREEN)

    assert available_leg_betting_ticket(state, CamelId.GREEN) is None


def test_taking_leg_ticket_transfers_the_highest_value_immutably() -> None:
    state = _setup_state()

    updated = take_leg_betting_ticket(state, player_id=1, camel=CamelId.GREEN)

    assert updated.players[1].leg_betting_tickets == (
        LegBettingTicket(camel=CamelId.GREEN, value=5),
    )
    assert tuple(
        ticket.value for ticket in _tickets_for_camel(updated, CamelId.GREEN)
    ) == (2, 2, 3)
    assert available_leg_betting_ticket(updated, CamelId.GREEN) == LegBettingTicket(
        camel=CamelId.GREEN,
        value=3,
    )
    assert state.players[1].leg_betting_tickets == ()
    assert (
        tuple(ticket.value for ticket in _tickets_for_camel(state, CamelId.GREEN))
        == LEG_BETTING_TICKET_STACK_VALUES
    )
    assert updated.players[1].money == state.players[1].money


def test_leg_tickets_follow_take_order_and_then_exhaust() -> None:
    state = _setup_state()

    taken_values: list[int] = []
    expected_take_order = tuple(reversed(LEG_BETTING_TICKET_STACK_VALUES))
    for draw_index, _ in enumerate(expected_take_order):
        ticket = available_leg_betting_ticket(state, CamelId.RED)
        assert ticket is not None
        taken_values.append(ticket.value)
        state = take_leg_betting_ticket(
            state,
            player_id=draw_index % MIN_PLAYERS,
            camel=CamelId.RED,
        )

    assert taken_values == list(expected_take_order)
    assert available_leg_betting_ticket(state, CamelId.RED) is None
    with pytest.raises(ValueError, match="no leg betting ticket"):
        take_leg_betting_ticket(state, player_id=0, camel=CamelId.RED)


def test_taking_different_colors_keeps_player_tickets_canonical() -> None:
    state = _setup_state()

    state = take_leg_betting_ticket(state, player_id=2, camel=CamelId.PURPLE)
    state = take_leg_betting_ticket(state, player_id=2, camel=CamelId.RED)

    assert state.players[2].leg_betting_tickets == (
        LegBettingTicket(camel=CamelId.RED, value=5),
        LegBettingTicket(camel=CamelId.PURPLE, value=5),
    )


def test_final_bets_remove_cards_and_keep_independent_ordered_records() -> None:
    state = _setup_state()

    state = place_final_bet(
        state,
        player_id=1,
        camel=CamelId.GREEN,
        target=FinalBetTarget.WINNER,
    )
    state = place_final_bet(
        state,
        player_id=0,
        camel=CamelId.RED,
        target=FinalBetTarget.LOSER,
    )
    state = place_final_bet(
        state,
        player_id=2,
        camel=CamelId.BLUE,
        target=FinalBetTarget.WINNER,
    )

    assert state.final_winner_bets == (
        FinalBet(player_id=1, camel=CamelId.GREEN),
        FinalBet(player_id=2, camel=CamelId.BLUE),
    )
    assert state.final_loser_bets == (FinalBet(player_id=0, camel=CamelId.RED),)
    assert CamelId.GREEN not in state.players[1].available_finish_cards
    assert CamelId.RED not in state.players[0].available_finish_cards
    assert CamelId.BLUE not in state.players[2].available_finish_cards
    assert all(player.money == 3 for player in state.players)


def test_finish_card_cannot_be_used_in_both_final_records() -> None:
    state = place_final_bet(
        _setup_state(),
        player_id=0,
        camel=CamelId.YELLOW,
        target=FinalBetTarget.WINNER,
    )

    with pytest.raises(ValueError, match="finish card is not available"):
        place_final_bet(
            state,
            player_id=0,
            camel=CamelId.YELLOW,
            target=FinalBetTarget.LOSER,
        )


@pytest.mark.parametrize("player_id", [-1, MIN_PLAYERS])
@pytest.mark.parametrize("bet_kind", ["leg", "final"])
def test_betting_rejects_unknown_player(player_id: int, bet_kind: str) -> None:
    state = _setup_state()

    with pytest.raises(ValueError, match="identify a player"):
        if bet_kind == "leg":
            take_leg_betting_ticket(state, player_id, CamelId.RED)
        else:
            place_final_bet(
                state,
                player_id,
                CamelId.RED,
                FinalBetTarget.WINNER,
            )


def test_betting_queries_and_transitions_reject_crazy_camels() -> None:
    state = _setup_state()

    with pytest.raises(ValueError, match="racing camel"):
        available_leg_betting_ticket(state, CamelId.WHITE)
    with pytest.raises(ValueError, match="racing camel"):
        take_leg_betting_ticket(state, 0, CamelId.BLACK)
    with pytest.raises(ValueError, match="racing camel"):
        place_final_bet(state, 0, CamelId.WHITE, FinalBetTarget.WINNER)


def test_final_bet_rejects_unknown_target() -> None:
    invalid_target = cast(FinalBetTarget, "podium")

    with pytest.raises(ValueError, match="winner or loser"):
        place_final_bet(_setup_state(), 0, CamelId.RED, invalid_target)


@pytest.mark.parametrize("bet_kind", ["leg", "final"])
@pytest.mark.parametrize("state_kind", ["pre-setup", "leg-complete", "terminal"])
def test_betting_rejects_inactive_game_states(
    bet_kind: str,
    state_kind: str,
) -> None:
    if state_kind == "pre-setup":
        state = GameState.pre_setup()
        message = "setup"
    elif state_kind == "leg-complete":
        state = replace(_setup_state(), remaining_dice=(DieId.GREY,))
        message = "leg is complete"
    else:
        state = replace(_setup_state(), terminal=True)
        message = "game has ended"

    with pytest.raises(ValueError, match=message):
        if bet_kind == "leg":
            take_leg_betting_ticket(state, 0, CamelId.RED)
        else:
            place_final_bet(state, 0, CamelId.RED, FinalBetTarget.WINNER)


def test_game_rejects_noncanonical_available_ticket_order() -> None:
    state = GameState.pre_setup()
    stacks = state.available_leg_betting_tickets
    red_stack = stacks[0]
    noncanonical_red_stack = (*red_stack[:2], red_stack[3], red_stack[2])

    with pytest.raises(ValueError, match="canonical stacks"):
        replace(
            state,
            available_leg_betting_tickets=(noncanonical_red_stack, *stacks[1:]),
        )


def test_game_rejects_missing_or_duplicated_leg_tickets() -> None:
    state = GameState.pre_setup()
    stacks = state.available_leg_betting_tickets

    with pytest.raises(ValueError, match="conserve the initial supply"):
        replace(
            state,
            available_leg_betting_tickets=(stacks[0][:-1], *stacks[1:]),
        )

    player = replace(
        state.players[0],
        leg_betting_tickets=(LegBettingTicket(camel=CamelId.RED, value=5),),
    )
    with pytest.raises(ValueError, match="conserve the initial supply"):
        replace(state, players=(player, *state.players[1:]))


def test_game_rejects_finish_card_missing_from_both_locations() -> None:
    state = GameState.pre_setup()
    player = replace(
        state.players[0],
        available_finish_cards=RACING_CAMEL_ORDER[1:],
    )

    with pytest.raises(ValueError, match="conserve one card"):
        replace(state, players=(player, *state.players[1:]))


def test_game_rejects_finish_card_in_both_final_records() -> None:
    state = place_final_bet(
        _setup_state(),
        player_id=0,
        camel=CamelId.RED,
        target=FinalBetTarget.WINNER,
    )
    bet = state.final_winner_bets[0]

    with pytest.raises(ValueError, match="conserve one card"):
        replace(state, final_loser_bets=(bet,))


def test_game_rejects_final_bet_for_player_outside_roster() -> None:
    state = _setup_state()

    with pytest.raises(ValueError, match="belong to a player"):
        replace(
            state,
            final_loser_bets=(FinalBet(player_id=MIN_PLAYERS, camel=CamelId.BLUE),),
        )


def test_equivalent_betting_histories_are_hashable() -> None:
    first = place_final_bet(
        take_leg_betting_ticket(_setup_state(), 0, CamelId.RED),
        1,
        CamelId.BLUE,
        FinalBetTarget.LOSER,
    )
    second = place_final_bet(
        take_leg_betting_ticket(_setup_state(), 0, CamelId.RED),
        1,
        CamelId.BLUE,
        FinalBetTarget.LOSER,
    )

    assert first == second
    assert hash(first) == hash(second)
    assert {first: "recorded"}[second] == "recorded"
