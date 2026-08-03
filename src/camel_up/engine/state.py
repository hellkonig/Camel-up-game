"""Canonical, immutable state containers for the Camel Up engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

CamelId: TypeAlias = Literal[
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "white",
    "black",
]
DieId: TypeAlias = Literal[
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "grey",
]

CAMEL_ORDER: tuple[CamelId, ...] = (
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "white",
    "black",
)
DIE_ORDER: tuple[DieId, ...] = (
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "grey",
)


@dataclass(frozen=True, slots=True)
class CamelPosition:
    """A camel's coordinate on the track and within its stack.

    Level zero is the bottom of a stack. An unplaced camel has both fields set
    to ``None``. Positions are the sole source of truth for camel placement;
    board stacks are derived from them.
    """

    space: int | None = None
    level: int | None = None

    def __post_init__(self) -> None:
        """Require a complete placed or unplaced coordinate."""
        if (self.space is None) != (self.level is None):
            raise ValueError("space and level must either both be set or both be None")
        if self.space is not None and self.space < 0:
            raise ValueError("space must be non-negative")
        if self.level is not None and self.level < 0:
            raise ValueError("level must be non-negative")

    @property
    def is_placed(self) -> bool:
        """Return whether the camel is currently on the board."""
        return self.space is not None


@dataclass(frozen=True, slots=True)
class SpectatorTile:
    """A player's spectator tile and its movement effect."""

    player_id: int
    space: int
    effect: Literal[-1, 1]

    def __post_init__(self) -> None:
        """Validate the state-independent parts of a tile coordinate."""
        if self.player_id < 0:
            raise ValueError("player_id must be non-negative")
        if self.space < 0:
            raise ValueError("space must be non-negative")
        if self.effect not in (-1, 1):
            raise ValueError("effect must be -1 or 1")


def _initial_camel_positions() -> tuple[CamelPosition, ...]:
    """Return one unplaced coordinate for each camel."""
    return tuple(CamelPosition() for _ in CAMEL_ORDER)


@dataclass(frozen=True, slots=True)
class BoardState:
    """Immutable track state with camel coordinates and spectator tiles.

    ``camel_positions`` uses :data:`CAMEL_ORDER`; its index is the camel's
    identity. Camels on the same space must occupy unique, contiguous levels
    beginning at zero.
    """

    track_length: int = 17
    camel_positions: tuple[CamelPosition, ...] = field(
        default_factory=_initial_camel_positions
    )
    spectator_tiles: tuple[SpectatorTile, ...] = ()

    def __post_init__(self) -> None:
        """Validate coordinates and canonical tile ordering."""
        if self.track_length <= 0:
            raise ValueError("track_length must be positive")
        if len(self.camel_positions) != len(CAMEL_ORDER):
            raise ValueError(f"camel_positions must contain {len(CAMEL_ORDER)} entries")

        levels_by_space: dict[int, list[int]] = {}
        for position in self.camel_positions:
            if not position.is_placed:
                continue
            assert position.space is not None
            assert position.level is not None
            if position.space >= self.track_length:
                raise ValueError("camel space must be within the track")
            levels_by_space.setdefault(position.space, []).append(position.level)

        for levels in levels_by_space.values():
            if sorted(levels) != list(range(len(levels))):
                raise ValueError("stack levels must be unique and contiguous from zero")

        player_ids = [tile.player_id for tile in self.spectator_tiles]
        if player_ids != sorted(player_ids) or len(player_ids) != len(set(player_ids)):
            raise ValueError("spectator tiles must be unique and ordered by player_id")

        tile_spaces = [tile.space for tile in self.spectator_tiles]
        if len(tile_spaces) != len(set(tile_spaces)):
            raise ValueError("spectator tiles cannot share a space")
        if any(space >= self.track_length for space in tile_spaces):
            raise ValueError("spectator tile space must be within the track")


@dataclass(frozen=True, slots=True)
class GameState:
    """Complete public state boundary for deterministic engine transitions.

    The state contains no random generator and exposes no mutation methods.
    Rule functions receive a state and return a replacement state atomically,
    which makes states safe to compare, hash, replay, and store in search trees.
    """

    board: BoardState = field(default_factory=BoardState)
    remaining_dice: tuple[DieId, ...] = DIE_ORDER
    current_player: int = 0
    leg_number: int = 1
    terminal: bool = False

    def __post_init__(self) -> None:
        """Validate canonical dice order and scalar state fields."""
        if len(self.remaining_dice) != len(set(self.remaining_dice)):
            raise ValueError("remaining_dice cannot contain duplicates")
        expected_order = tuple(
            die for die in DIE_ORDER if die in self.remaining_dice
        )
        if self.remaining_dice != expected_order:
            raise ValueError("remaining_dice must be valid and use canonical order")
        if self.current_player < 0:
            raise ValueError("current_player must be non-negative")
        if self.leg_number < 1:
            raise ValueError("leg_number must be positive")


def position_of(state: GameState, camel: CamelId) -> CamelPosition:
    """Return the authoritative coordinate for ``camel``."""
    return state.board.camel_positions[CAMEL_ORDER.index(camel)]


def stack_at(state: GameState, space: int) -> tuple[CamelId, ...]:
    """Return the stack at ``space`` ordered from bottom to top."""
    if not 0 <= space < state.board.track_length:
        raise ValueError("space must be within the track")

    stack: list[tuple[int, CamelId]] = []
    for camel, position in zip(CAMEL_ORDER, state.board.camel_positions):
        if position.space == space:
            assert position.level is not None
            stack.append((position.level, camel))
    return tuple(camel for _, camel in sorted(stack))


def carried_camels(state: GameState, camel: CamelId) -> tuple[CamelId, ...]:
    """Return ``camel`` and every camel above it, bottom to top."""
    position = position_of(state, camel)
    if not position.is_placed:
        raise ValueError("camel must be placed before it can carry a stack")
    assert position.space is not None
    assert position.level is not None
    return stack_at(state, position.space)[position.level :]
