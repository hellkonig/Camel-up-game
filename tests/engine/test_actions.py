from dataclasses import replace
from typing import Literal, cast

import pytest

from camel_up.engine import (
    CAMEL_ORDER,
    DIE_ORDER,
    MIN_PLAYERS,
    RACING_CAMEL_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    FinalBetTarget,
    GameState,
    PlaceFinalBetAction,
    PlaceSpectatorTileAction,
    PlayerState,
    RollAction,
    SpectatorTile,
    TakeLegBettingTicketAction,
    get_action_space,
    get_legal_action_mask,
    get_legal_actions,
    place_final_bet,
    place_spectator_tile,
    take_leg_betting_ticket,
)


def _active_state(
    *,
    current_player: int = 0,
    spectator_tiles: tuple[SpectatorTile, ...] = (),
    single_stack: bool = False,
) -> GameState:
    """Build a deterministic, fully placed state at a player boundary."""
    if single_stack:
        camel_positions = tuple(
            CamelPosition(space=2, level=level) for level, _ in enumerate(CAMEL_ORDER)
        )
    else:
        camel_positions = tuple(
            CamelPosition(space=2 + index * 2, level=0)
            for index, _ in enumerate(CAMEL_ORDER)
        )

    return GameState(
        board=BoardState(
            track_length=16,
            camel_positions=camel_positions,
            spectator_tiles=spectator_tiles,
        ),
        players=tuple(PlayerState(player_id=index) for index in range(MIN_PLAYERS)),
        current_player=current_player,
    )


def test_action_space_has_stable_documented_order() -> None:
    action_space = get_action_space(16)
    final_bet_start = 1 + len(RACING_CAMEL_ORDER) + 2 * 15

    assert len(action_space) == 46
    assert action_space[:6] == (
        RollAction(),
        *(TakeLegBettingTicketAction(camel) for camel in RACING_CAMEL_ORDER),
    )
    assert action_space[6:10] == (
        PlaceSpectatorTileAction(space=1, effect=1),
        PlaceSpectatorTileAction(space=1, effect=-1),
        PlaceSpectatorTileAction(space=2, effect=1),
        PlaceSpectatorTileAction(space=2, effect=-1),
    )
    assert action_space[final_bet_start - 2 : final_bet_start] == (
        PlaceSpectatorTileAction(space=15, effect=1),
        PlaceSpectatorTileAction(space=15, effect=-1),
    )
    assert action_space[final_bet_start:] == tuple(
        PlaceFinalBetAction(camel=camel, target=target)
        for target in (FinalBetTarget.WINNER, FinalBetTarget.LOSER)
        for camel in RACING_CAMEL_ORDER
    )


def test_action_space_scales_with_track_length_and_rejects_invalid_length() -> None:
    assert len(get_action_space(8)) == 30
    assert PlaceSpectatorTileAction(space=8, effect=1) not in get_action_space(8)
    with pytest.raises(ValueError, match="positive"):
        get_action_space(0)


def test_actions_validate_state_independent_fields() -> None:
    with pytest.raises(ValueError, match="racing camel"):
        TakeLegBettingTicketAction(CamelId.WHITE)
    with pytest.raises(ValueError, match="racing camel"):
        PlaceFinalBetAction(CamelId.BLACK, FinalBetTarget.WINNER)
    with pytest.raises(ValueError, match="non-negative"):
        PlaceSpectatorTileAction(space=-1, effect=1)
    with pytest.raises(ValueError, match="-1 or 1"):
        PlaceSpectatorTileAction(space=3, effect=cast(Literal[-1, 1], 0))


def test_legal_actions_are_derived_from_the_canonical_mask() -> None:
    state = _active_state()
    original_hash = hash(state)
    action_space = get_action_space(state.board.track_length)

    mask = get_legal_action_mask(state, player_id=0)
    legal_actions = get_legal_actions(state, player_id=0)

    assert len(mask) == len(action_space)
    assert legal_actions == tuple(
        action for action, is_legal in zip(action_space, mask, strict=True) if is_legal
    )
    assert len(legal_actions) == 32
    assert mask[0]
    assert state == _active_state()
    assert hash(state) == original_hash


def test_unavailable_betting_assets_are_not_legal_actions() -> None:
    state = _active_state()
    for _ in range(4):
        state = take_leg_betting_ticket(state, player_id=0, camel=CamelId.RED)
    state = place_final_bet(
        state,
        player_id=0,
        camel=CamelId.BLUE,
        target=FinalBetTarget.WINNER,
    )

    legal_actions = get_legal_actions(state, player_id=0)

    assert TakeLegBettingTicketAction(CamelId.RED) not in legal_actions
    assert all(
        PlaceFinalBetAction(CamelId.BLUE, target) not in legal_actions
        for target in FinalBetTarget
    )
    assert all(
        PlaceFinalBetAction(CamelId.GREEN, target) in legal_actions
        for target in FinalBetTarget
    )


def test_tile_actions_follow_placement_and_replacement_rules() -> None:
    state = _active_state(
        single_stack=True,
        spectator_tiles=(
            SpectatorTile(player_id=0, space=4, effect=1),
            SpectatorTile(player_id=1, space=7, effect=-1),
        ),
    )

    legal_actions = get_legal_actions(state, player_id=0)

    for effect in (1, -1):
        typed_effect = cast(Literal[-1, 1], effect)
        # Player 0's tile leaves space 4 before its new position is validated,
        # so the old tile does not make its former neighbor at space 3 illegal.
        assert PlaceSpectatorTileAction(3, typed_effect) in legal_actions
        assert PlaceSpectatorTileAction(4, typed_effect) not in legal_actions
        assert PlaceSpectatorTileAction(6, typed_effect) not in legal_actions
        assert PlaceSpectatorTileAction(7, typed_effect) not in legal_actions
        assert PlaceSpectatorTileAction(8, typed_effect) not in legal_actions


def test_tile_actions_and_transition_agree_for_every_candidate() -> None:
    state = _active_state(
        single_stack=True,
        spectator_tiles=(
            SpectatorTile(player_id=0, space=4, effect=1),
            SpectatorTile(player_id=1, space=7, effect=-1),
        ),
    )
    legal_actions = frozenset(get_legal_actions(state, player_id=0))
    tile_actions = (
        action
        for action in get_action_space(state.board.track_length)
        if isinstance(action, PlaceSpectatorTileAction)
    )

    for action in tile_actions:
        if action in legal_actions:
            updated = place_spectator_tile(
                state,
                player_id=0,
                space=action.space,
                effect=action.effect,
            )
            assert updated.board.spectator_tiles[0] == SpectatorTile(
                player_id=0,
                space=action.space,
                effect=action.effect,
            )
        else:
            with pytest.raises(ValueError):
                place_spectator_tile(
                    state,
                    player_id=0,
                    space=action.space,
                    effect=action.effect,
                )


@pytest.mark.parametrize(
    "state",
    [
        GameState.pre_setup(),
        replace(_active_state(), remaining_dice=(DieId.GREY,)),
        replace(_active_state(), terminal=True),
    ],
)
def test_inactive_states_have_no_player_actions(state: GameState) -> None:
    assert get_legal_actions(state, player_id=0) == ()
    assert not any(get_legal_action_mask(state, player_id=0))


def test_non_current_player_has_no_legal_actions() -> None:
    state = _active_state(current_player=1)

    assert get_legal_actions(state, player_id=0) == ()
    assert get_legal_action_mask(state, player_id=0) == tuple(
        False for _ in get_action_space(state.board.track_length)
    )
    assert get_legal_actions(state, player_id=1)


@pytest.mark.parametrize("player_id", [-1, MIN_PLAYERS])
def test_action_queries_reject_unknown_players(player_id: int) -> None:
    state = _active_state()

    with pytest.raises(ValueError, match="identify a player"):
        get_legal_action_mask(state, player_id)
    with pytest.raises(ValueError, match="identify a player"):
        get_legal_actions(state, player_id)


def test_equivalent_states_expose_identical_actions_and_masks() -> None:
    state = _active_state()
    equivalent_state = replace(state, remaining_dice=DIE_ORDER)

    assert equivalent_state == state
    assert get_legal_action_mask(equivalent_state, 0) == get_legal_action_mask(state, 0)
    assert get_legal_actions(equivalent_state, 0) == get_legal_actions(state, 0)
