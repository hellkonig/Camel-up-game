"""Typed player choices and deterministic legal-action masks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from camel_up.engine.betting import (
    legal_final_betting_camels,
    legal_leg_betting_camels,
)
from camel_up.engine.dice import can_roll_die
from camel_up.engine.state import (
    RACING_CAMEL_ORDER,
    CamelId,
    FinalBetTarget,
    GameState,
)
from camel_up.engine.tiles import legal_spectator_tile_spaces

# These orders are part of the stable public action-index contract.
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
    """Parameter-free choice to take a pyramid ticket and roll a die.

    The random die result belongs to action application, so this value only
    identifies the player's choice within the action space.
    """


@dataclass(frozen=True, slots=True)
class PlaceSpectatorTileAction:
    """Place or move the current player's spectator tile.

    Track bounds depend on a particular game state and are therefore checked
    by legal-action generation and action application, not by this value type.
    """

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
    if player_id != state.current_player:
        return tuple(False for _ in action_space)

    leg_betting_camels = frozenset(legal_leg_betting_camels(state, player_id))
    tile_spaces = frozenset(legal_spectator_tile_spaces(state, player_id))
    final_betting_camels = frozenset(legal_final_betting_camels(state, player_id))
    return tuple(
        _is_legal_action(
            state,
            action,
            leg_betting_camels,
            tile_spaces,
            final_betting_camels,
        )
        for action in action_space
    )


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


def _is_legal_action(
    state: GameState,
    action: Action,
    leg_betting_camels: frozenset[CamelId],
    tile_spaces: frozenset[int],
    final_betting_camels: frozenset[CamelId],
) -> bool:
    """Match one candidate against rule-owned legality queries."""
    if isinstance(action, RollAction):
        return can_roll_die(state)
    if isinstance(action, PlaceSpectatorTileAction):
        return action.space in tile_spaces
    if isinstance(action, TakeLegBettingTicketAction):
        return action.camel in leg_betting_camels
    if isinstance(action, PlaceFinalBetAction):
        return action.camel in final_betting_camels
    raise TypeError(f"unsupported action type: {type(action).__name__}")
