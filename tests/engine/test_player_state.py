from dataclasses import replace

import pytest

from camel_up.engine import (
    MAX_PLAYERS,
    MIN_PLAYERS,
    RACING_CAMEL_ORDER,
    BoardState,
    CamelId,
    GameState,
    LegBettingTicket,
    PlayerState,
    SpectatorTile,
    spectator_tile_for_player,
)


def _players(count: int = MIN_PLAYERS) -> tuple[PlayerState, ...]:
    return tuple(PlayerState(player_id=index) for index in range(count))


def test_pre_setup_creates_canonical_players_with_starting_assets() -> None:
    state = GameState.pre_setup()

    assert tuple(player.player_id for player in state.players) == tuple(
        range(MIN_PLAYERS)
    )
    assert all(player.money == 3 for player in state.players)
    assert all(player.pyramid_ticket_count == 0 for player in state.players)
    assert all(not player.leg_betting_tickets for player in state.players)
    assert all(
        player.available_finish_cards == RACING_CAMEL_ORDER for player in state.players
    )


def test_pre_setup_accepts_the_maximum_player_count() -> None:
    state = GameState.pre_setup(player_count=MAX_PLAYERS)

    assert len(state.players) == MAX_PLAYERS
    assert state.players[-1].player_id == MAX_PLAYERS - 1


@pytest.mark.parametrize("player_count", [MIN_PLAYERS - 1, MAX_PLAYERS + 1])
def test_game_rejects_player_count_outside_supported_range(
    player_count: int,
) -> None:
    with pytest.raises(ValueError, match="between 3 and 8"):
        GameState.pre_setup(player_count=player_count)


@pytest.mark.parametrize(
    "players",
    [
        (PlayerState(player_id=1), PlayerState(player_id=0), PlayerState(player_id=2)),
        (PlayerState(player_id=0), PlayerState(player_id=2), PlayerState(player_id=3)),
        (PlayerState(player_id=0), PlayerState(player_id=1), PlayerState(player_id=1)),
    ],
)
def test_game_requires_players_in_contiguous_player_id_order(
    players: tuple[PlayerState, ...],
) -> None:
    with pytest.raises(ValueError, match="contiguous player_id"):
        GameState(board=BoardState.empty(), players=players)


@pytest.mark.parametrize("current_player", [-1, MIN_PLAYERS])
def test_current_player_must_identify_a_player(current_player: int) -> None:
    with pytest.raises(ValueError, match="identify a player"):
        GameState(
            board=BoardState.empty(),
            players=_players(),
            current_player=current_player,
        )


def test_spectator_tile_must_belong_to_a_game_player() -> None:
    board = BoardState(
        track_length=16,
        camel_positions=BoardState.empty().camel_positions,
        spectator_tiles=(SpectatorTile(player_id=MIN_PLAYERS, space=3, effect=1),),
    )

    with pytest.raises(ValueError, match="belong to a player"):
        GameState(board=board, players=_players())


def test_spectator_tile_placement_is_derived_from_board_state() -> None:
    tile = SpectatorTile(player_id=1, space=3, effect=-1)
    state = GameState(
        board=BoardState(
            track_length=16,
            camel_positions=BoardState.empty().camel_positions,
            spectator_tiles=(tile,),
        ),
        players=_players(),
    )

    assert spectator_tile_for_player(state, 0) is None
    assert spectator_tile_for_player(state, 1) == tile
    assert not hasattr(state.players[1], "spectator_tile")

    with pytest.raises(ValueError, match="identify a player"):
        spectator_tile_for_player(state, MIN_PLAYERS)


@pytest.mark.parametrize(
    ("player_kwargs", "message"),
    [
        pytest.param({"player_id": -1}, "player_id", id="player-id"),
        pytest.param(
            {"player_id": 0, "money": -1},
            "money",
            id="money",
        ),
        pytest.param(
            {"player_id": 0, "pyramid_ticket_count": -1},
            "pyramid_ticket_count",
            id="pyramid-ticket-count",
        ),
    ],
)
def test_player_rejects_negative_scalar_resources(
    player_kwargs: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PlayerState(**player_kwargs)


@pytest.mark.parametrize(
    "ticket",
    [
        LegBettingTicket(camel=CamelId.RED, value=5),
        LegBettingTicket(camel=CamelId.BLUE, value=3),
        LegBettingTicket(camel=CamelId.PURPLE, value=2),
    ],
)
def test_leg_betting_ticket_accepts_printed_racing_tickets(
    ticket: LegBettingTicket,
) -> None:
    assert ticket.camel in RACING_CAMEL_ORDER


def test_leg_betting_ticket_rejects_crazy_camels_and_unknown_values() -> None:
    with pytest.raises(ValueError, match="racing camel"):
        LegBettingTicket(camel=CamelId.WHITE, value=5)
    with pytest.raises(ValueError, match="2, 3, or 5"):
        LegBettingTicket(camel=CamelId.RED, value=4)


def test_player_accepts_tickets_ordered_by_camel_then_descending_value() -> None:
    red_five = LegBettingTicket(camel=CamelId.RED, value=5)
    red_two = LegBettingTicket(camel=CamelId.RED, value=2)
    blue_three = LegBettingTicket(camel=CamelId.BLUE, value=3)

    player = PlayerState(
        player_id=0,
        leg_betting_tickets=(red_five, red_two, blue_three),
    )

    assert player.leg_betting_tickets == (red_five, red_two, blue_three)


def test_player_rejects_ticket_camel_order() -> None:
    red_five = LegBettingTicket(camel=CamelId.RED, value=5)
    blue_three = LegBettingTicket(camel=CamelId.BLUE, value=3)

    with pytest.raises(ValueError, match="canonical order"):
        PlayerState(
            player_id=0,
            leg_betting_tickets=(blue_three, red_five),
        )


def test_player_rejects_ascending_ticket_values_for_one_camel() -> None:
    red_five = LegBettingTicket(camel=CamelId.RED, value=5)
    red_two = LegBettingTicket(camel=CamelId.RED, value=2)

    with pytest.raises(ValueError, match="canonical order"):
        PlayerState(
            player_id=0,
            leg_betting_tickets=(red_two, red_five),
        )


@pytest.mark.parametrize(
    "cards",
    [
        (CamelId.RED, CamelId.RED),
        (CamelId.RED, CamelId.WHITE),
        (CamelId.BLUE, CamelId.RED),
    ],
    ids=["duplicate", "crazy-camel", "noncanonical-order"],
)
def test_player_rejects_invalid_available_finish_cards(
    cards: tuple[CamelId, ...],
) -> None:
    with pytest.raises(ValueError, match="available_finish_cards"):
        PlayerState(player_id=0, available_finish_cards=cards)


def test_player_accepts_canonical_subset_of_available_finish_cards() -> None:
    cards = (CamelId.RED, CamelId.GREEN, CamelId.PURPLE)

    player = PlayerState(player_id=0, available_finish_cards=cards)

    assert player.available_finish_cards == cards


def test_equivalent_player_states_are_hashable_and_replaceable() -> None:
    ticket = LegBettingTicket(camel=CamelId.GREEN, value=3)
    player = PlayerState(
        player_id=0,
        money=6,
        pyramid_ticket_count=2,
        leg_betting_tickets=(ticket,),
        available_finish_cards=(CamelId.RED, CamelId.BLUE),
    )
    equivalent = PlayerState(
        player_id=0,
        money=6,
        pyramid_ticket_count=2,
        leg_betting_tickets=(ticket,),
        available_finish_cards=(CamelId.RED, CamelId.BLUE),
    )
    updated = replace(player, money=7)

    transpositions = {player: "original", updated: "updated"}

    assert player == equivalent
    assert hash(player) == hash(equivalent)
    assert player.money == 6
    assert updated.money == 7
    assert transpositions[equivalent] == "original"
