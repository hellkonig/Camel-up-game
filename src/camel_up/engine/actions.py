"""Typed player choices and deterministic legal-action masks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from camel_up.engine.betting import place_final_bet, take_leg_betting_ticket
from camel_up.engine.state import (
    RACING_CAMEL_ORDER,
    CamelId,
    FinalBetTarget,
    GameState,
)
from camel_up.engine.tiles import place_spectator_tile

_SPECTATOR_TILE_EFFECT_ORDER: Final[tuple[Literal[-1, 1], ...]] = (1, -1)
_FINAL_BET_TARGET_ORDER: Final = (
    FinalBetTarget.WINNER,
    FinalBetTarget.LOSER,
)


def _validate_racing_camel(camel: CamelId) -> None:
    """Require a racing-camel identity for a betting action."""
    if not isinstance(camel, CamelId) or camel not in RACING_CAMEL_ORDER:
        raise ValueError(f"betting actions require a racing camel, got {camel!r}")


@dataclass(frozen=True, slots=True)
class RollAction:
    """Take a pyramid ticket and roll one of the remaining dice."""


@dataclass(frozen=True, slots=True)
class PlaceSpectatorTileAction:
    """Place or move the current player's spectator tile."""

    space: int
    effect: Literal[-1, 1]

    def __post_init__(self) -> None:
        """Validate the state-independent action fields."""
        if self.space < 0:
            raise ValueError("spectator tile space must be non-negative")
        if self.effect not in (-1, 1):
            raise ValueError("spectator tile effect must be -1 or 1")


@dataclass(frozen=True, slots=True)
class TakeLegBettingTicketAction:
    """Take the top available leg ticket for one racing camel."""

    camel: CamelId

    def __post_init__(self) -> None:
        """Reject crazy-camel and non-camel predictions."""
        _validate_racing_camel(self.camel)


@dataclass(frozen=True, slots=True)
class PlaceFinalBetAction:
    """Place one finish card into the winner or loser record."""

    camel: CamelId
    target: FinalBetTarget

    def __post_init__(self) -> None:
        """Validate the state-independent action fields."""
        _validate_racing_camel(self.camel)
        if not isinstance(self.target, FinalBetTarget):
            raise ValueError(
                f"final bet target must be winner or loser, got {self.target!r}"
            )


Action: TypeAlias = (
    RollAction
    | PlaceSpectatorTileAction
    | TakeLegBettingTicketAction
    | PlaceFinalBetAction
)


def get_action_space(track_length: int) -> tuple[Action, ...]:
    """Return the complete, stably indexed action space for a track.

    The order is one roll action; leg bets in racing-camel identity order;
    spectator-tile placements in ascending space order, cheering before
    booing; then final winner and loser bets in racing-camel identity order.
    Track space zero is excluded because a spectator tile can never occupy it.

    Args:
        track_length: Number of playable spaces on the configured board.

    Returns:
        Every structurally possible action, including currently illegal ones.

    Raises:
        ValueError: If ``track_length`` is not positive.
    """
    if track_length <= 0:
        raise ValueError("track_length must be positive")

    leg_bet_actions = tuple(
        TakeLegBettingTicketAction(camel) for camel in RACING_CAMEL_ORDER
    )
    tile_actions = tuple(
        PlaceSpectatorTileAction(space=space, effect=effect)
        for space in range(1, track_length)
        for effect in _SPECTATOR_TILE_EFFECT_ORDER
    )
    final_bet_actions = tuple(
        PlaceFinalBetAction(camel=camel, target=target)
        for target in _FINAL_BET_TARGET_ORDER
        for camel in RACING_CAMEL_ORDER
    )
    return (RollAction(), *leg_bet_actions, *tile_actions, *final_bet_actions)


def get_legal_action_mask(
    state: GameState,
    player_id: int,
) -> tuple[bool, ...]:
    """Return a mask aligned with :func:`get_action_space`.

    A valid player who is not the current player has no legal actions. Setup,
    leg-boundary, and terminal states likewise expose an all-false mask because
    their next transitions are orchestration rather than player choices.

    Args:
        state: Current immutable engine state.
        player_id: Stable identity of the querying player.

    Returns:
        One boolean for every action-space entry.

    Raises:
        ValueError: If ``player_id`` does not identify a player.
    """
    if not 0 <= player_id < len(state.players):
        raise ValueError(f"player_id {player_id} must identify a player in players")

    action_space = get_action_space(state.board.track_length)
    if player_id != state.current_player or not _accepts_player_action(state):
        return tuple(False for _ in action_space)

    return tuple(_is_legal_action(state, player_id, action) for action in action_space)


def get_legal_actions(
    state: GameState,
    player_id: int,
) -> tuple[Action, ...]:
    """Return legal typed choices derived from the canonical action mask."""
    action_space = get_action_space(state.board.track_length)
    mask = get_legal_action_mask(state, player_id)
    return tuple(
        action for action, is_legal in zip(action_space, mask, strict=True) if is_legal
    )


def _accepts_player_action(state: GameState) -> bool:
    """Return whether the state is at an active player-choice boundary."""
    return (
        all(position.is_placed for position in state.board.camel_positions)
        and not state.terminal
        and len(state.remaining_dice) > 1
    )


def _is_legal_action(
    state: GameState,
    player_id: int,
    action: Action,
) -> bool:
    """Check one candidate through the rule transition that would apply it."""
    if isinstance(action, RollAction):
        return True

    try:
        if isinstance(action, PlaceSpectatorTileAction):
            place_spectator_tile(
                state,
                player_id=player_id,
                space=action.space,
                effect=action.effect,
            )
        elif isinstance(action, TakeLegBettingTicketAction):
            take_leg_betting_ticket(state, player_id=player_id, camel=action.camel)
        else:
            place_final_bet(
                state,
                player_id=player_id,
                camel=action.camel,
                target=action.target,
            )
    except ValueError:
        return False
    return True
