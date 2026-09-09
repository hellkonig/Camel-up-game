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
    error = _spectator_tile_placement_error(state, player_id, space, effect)
    if error is not None:
        raise ValueError(error)

    tile = SpectatorTile(player_id=player_id, space=space, effect=effect)
    other_tiles = tuple(
        placed_tile
        for placed_tile in state.board.spectator_tiles
        if placed_tile.player_id != player_id
    )
    # Stable player-ID order gives equivalent states identical equality and hashes.
    spectator_tiles = tuple(
        sorted((*other_tiles, tile), key=lambda placed_tile: placed_tile.player_id)
    )
    board = replace(state.board, spectator_tiles=spectator_tiles)
    return replace(state, board=board)


def can_place_spectator_tile(
    state: GameState,
    player_id: int,
    space: int,
    effect: Literal[-1, 1],
) -> bool:
    """Return whether a tile placement is legal without creating a new state."""
    return _spectator_tile_placement_error(state, player_id, space, effect) is None


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


def _spectator_tile_placement_error(
    state: GameState,
    player_id: int,
    space: int,
    effect: Literal[-1, 1],
) -> str | None:
    """Return the first placement error shared by queries and transitions."""
    if not 0 <= player_id < len(state.players):
        return f"player_id {player_id} must identify a player in players"
    if not all(position.is_placed for position in state.board.camel_positions):
        return "initial setup must be completed before placing a tile"
    if state.terminal:
        return "cannot place a spectator tile after the game has ended"
    if len(state.remaining_dice) <= 1:
        return "the leg is complete; settle it before placing a tile"

    existing_tile = next(
        (tile for tile in state.board.spectator_tiles if tile.player_id == player_id),
        None,
    )
    if existing_tile is not None and existing_tile.space == space:
        return "a spectator tile must move to a different space"
    if space < 0:
        return "spectator tile space must be non-negative"
    if effect not in (-1, 1):
        return "spectator tile effect must be -1 or 1"

    other_tiles = tuple(
        tile for tile in state.board.spectator_tiles if tile.player_id != player_id
    )
    if any(tile.space == space for tile in other_tiles):
        return "spectator tiles cannot share a space"
    if space >= state.board.track_length:
        return "spectator tile space must be within the track"
    if space == 0:
        return "spectator tiles cannot be placed on track space 1"
    if any(position.space == space for position in state.board.camel_positions):
        return "spectator tiles cannot share a space with camels"
    if any(abs(tile.space - space) == 1 for tile in other_tiles):
        return "spectator tiles cannot be on adjacent spaces"
    return None


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
