"""Deterministic spectator-tile placement and effect rules."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from camel_up.engine.state import (
    BoardState,
    CamelId,
    GameState,
    PlayerState,
    SpectatorTile,
)

_CRAZY_CAMELS = (CamelId.WHITE, CamelId.BLACK)


def place_spectator_tile(
    state: GameState,
    player_id: int,
    space: int,
    effect: Literal[-1, 1],
) -> GameState:
    """Place or move one player's spectator tile.

    Placement-specific board constraints are enforced by :class:`BoardState`:
    the space must be empty, cannot be the first track space, and cannot be
    adjacent to another spectator tile. A previously placed tile is removed
    before the replacement position is validated.

    This transition does not enforce whose turn it is. The future action layer
    owns turn legality.

    Args:
        state: Active game state before placement.
        player_id: Stable identity of the tile owner.
        space: Zero-based track coordinate for the tile.
        effect: ``1`` for cheering or ``-1`` for booing.

    Returns:
        A replacement state containing the canonically ordered tile.

    Raises:
        ValueError: If placement is unavailable or violates a tile rule.
    """
    _validate_tile_transition(state, player_id)
    existing_tile = next(
        (tile for tile in state.board.spectator_tiles if tile.player_id == player_id),
        None,
    )
    if existing_tile is not None and existing_tile.space == space:
        raise ValueError("a spectator tile must move to a different space")

    tile = SpectatorTile(player_id=player_id, space=space, effect=effect)
    other_tiles = tuple(
        placed_tile
        for placed_tile in state.board.spectator_tiles
        if placed_tile.player_id != player_id
    )
    spectator_tiles = tuple(
        sorted((*other_tiles, tile), key=lambda placed_tile: placed_tile.player_id)
    )
    board = replace(state.board, spectator_tiles=spectator_tiles)
    return replace(state, board=board)


def return_spectator_tiles(state: GameState) -> GameState:
    """Return all placed spectator tiles at a leg boundary.

    This tile-only transition is intended for later turn orchestration. It
    leaves dice, scoring assets, player order, and the leg number unchanged.

    Args:
        state: A completed leg or terminal game.

    Returns:
        A replacement state with no spectator tiles on the board.

    Raises:
        ValueError: If setup is incomplete or the leg is still active.
    """
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before returning tiles")
    if not state.terminal and len(state.remaining_dice) != 1:
        raise ValueError("spectator tiles can only return at a leg boundary")
    if not state.board.spectator_tiles:
        return state
    return replace(state, board=replace(state.board, spectator_tiles=()))


def apply_spectator_tile_effect(
    state: GameState,
    moving_camel: CamelId,
    landing_space: int,
) -> tuple[GameState, int, bool]:
    """Apply the reward and displacement for a tile landing.

    Args:
        state: State immediately before the camel unit is placed.
        moving_camel: Bottom camel of the moving unit.
        landing_space: Space reached by the die movement.

    Returns:
        The rewarded state, displaced destination, and whether the moving unit
        must be placed underneath the destination stack.
    """
    tile = _tile_at(state.board, landing_space)
    if tile is None:
        return state, landing_space, False

    travel_direction = -1 if moving_camel in _CRAZY_CAMELS else 1
    destination = landing_space + tile.effect * travel_direction
    owner = state.players[tile.player_id]
    rewarded_owner = replace(owner, money=owner.money + 1)
    players = _replace_player(state.players, rewarded_owner)
    return replace(state, players=players), destination, tile.effect == -1


def _tile_at(board: BoardState, space: int) -> SpectatorTile | None:
    """Return the spectator tile at ``space``, if one is present."""
    return next((tile for tile in board.spectator_tiles if tile.space == space), None)


def _validate_tile_transition(state: GameState, player_id: int) -> None:
    """Reject states and player identities that cannot place a tile."""
    if not 0 <= player_id < len(state.players):
        raise ValueError(f"player_id {player_id} must identify a player in players")
    if not all(position.is_placed for position in state.board.camel_positions):
        raise ValueError("initial setup must be completed before placing a tile")
    if state.terminal:
        raise ValueError("cannot place a spectator tile after the game has ended")
    if len(state.remaining_dice) <= 1:
        raise ValueError("the leg is complete; settle it before placing a tile")


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
