"""Canonical, immutable state containers for the Camel Up engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Final, Literal


class CamelId(str, Enum):
    """Stable identities for the five racing and two crazy camels."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    PURPLE = "purple"
    WHITE = "white"
    BLACK = "black"


class DieId(str, Enum):
    """Stable identities for the dice available during a leg."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    PURPLE = "purple"
    GREY = "grey"


CAMEL_ORDER: Final = tuple(CamelId)
DIE_ORDER: Final = tuple(DieId)
_CAMEL_INDEX: Final = MappingProxyType(
    {camel: index for index, camel in enumerate(CAMEL_ORDER)}
)


@dataclass(frozen=True, slots=True)
class CamelPosition:
    """A camel's coordinate on the track and within its stack.

    Level zero is the bottom of a stack. An unplaced camel has both fields set
    to ``None``. Finish zones use space ``-1`` for backward crossing and
    ``BoardState.track_length`` for forward crossing. Positions are the sole
    source of truth for camel placement; board stacks are derived from them.
    """

    space: int | None = None
    level: int | None = None

    def __post_init__(self) -> None:
        """Require a complete placed or unplaced coordinate."""
        if (self.space is None) != (self.level is None):
            raise ValueError("space and level must either both be set or both be None")
        if self.space is not None and self.space < -1:
            raise ValueError("space cannot be before the backward finish zone")
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


@dataclass(frozen=True, slots=True)
class BoardState:
    """Immutable track state with camel coordinates and spectator tiles.

    ``track_length`` is the number of playable spaces, indexed from zero.
    ``camel_positions`` uses :data:`CAMEL_ORDER`; its index is the camel's
    identity. Camels on the same space must occupy unique, contiguous levels
    beginning at zero. A terminal camel unit may occupy finish zone ``-1`` or
    ``track_length``. ``spectator_tiles`` is ordered by ``player_id`` so that
    logically equivalent snapshots compare and hash identically. A snapshot
    contains either no placed camels before setup or all camels after setup;
    initial placement is committed as one atomic state transition.
    """

    track_length: int
    camel_positions: tuple[CamelPosition, ...]
    spectator_tiles: tuple[SpectatorTile, ...] = ()

    @classmethod
    def empty(cls, track_length: int = 16) -> BoardState:
        """Create the deterministic board state before initial dice rolls.

        Starting camel positions depend on random die outcomes. The future
        seeded setup transition will calculate every position before creating
        the next snapshot, so individual setup rolls do not expose partially
        placed board states.
        """
        return cls(
            track_length=track_length,
            camel_positions=tuple(CamelPosition() for _ in CAMEL_ORDER),
        )

    def __post_init__(self) -> None:
        """Validate every newly constructed initial or mid-game snapshot."""
        if self.track_length <= 0:
            raise ValueError("track_length must be positive")
        if len(self.camel_positions) != len(CAMEL_ORDER):
            raise ValueError(f"camel_positions must contain {len(CAMEL_ORDER)} entries")

        occupied_spaces = self._validate_camel_positions()
        self._validate_spectator_tiles(occupied_spaces)

    def _validate_camel_positions(self) -> set[int]:
        """Validate camel coordinates and return occupied track spaces."""
        levels_by_space: dict[int, list[int]] = {}
        placed_count = 0
        for position in self.camel_positions:
            if position.space is None or position.level is None:
                continue
            placed_count += 1
            if position.space > self.track_length:
                raise ValueError("camel space cannot pass a finish zone")
            levels_by_space.setdefault(position.space, []).append(position.level)

        if placed_count not in (0, len(CAMEL_ORDER)):
            raise ValueError("camels must be either all unplaced or all placed")

        for levels in levels_by_space.values():
            if sorted(levels) != list(range(len(levels))):
                raise ValueError("stack levels must be unique and contiguous from zero")

        occupied_spaces = set(levels_by_space)
        return occupied_spaces

    def _validate_spectator_tiles(self, occupied_spaces: set[int]) -> None:
        """Validate tiles for initial and populated mid-game snapshots."""
        player_ids = [tile.player_id for tile in self.spectator_tiles]
        if player_ids != sorted(player_ids) or len(player_ids) != len(set(player_ids)):
            raise ValueError("spectator tiles must be unique and ordered by player_id")

        tile_spaces = [tile.space for tile in self.spectator_tiles]
        if len(tile_spaces) != len(set(tile_spaces)):
            raise ValueError("spectator tiles cannot share a space")
        if any(space >= self.track_length for space in tile_spaces):
            raise ValueError("spectator tile space must be within the track")
        if 0 in tile_spaces:
            raise ValueError("spectator tiles cannot be placed on track space 1")
        if occupied_spaces.intersection(tile_spaces):
            raise ValueError("spectator tiles cannot share a space with camels")

        sorted_spaces = sorted(tile_spaces)
        if any(
            right_space - left_space == 1
            for left_space, right_space in zip(
                sorted_spaces, sorted_spaces[1:], strict=False
            )
        ):
            raise ValueError("spectator tiles cannot be on adjacent spaces")


@dataclass(frozen=True, slots=True)
class GameState:
    """Public state foundation for deterministic engine transitions.

    The state contains no random generator and exposes no mutation methods.
    Rule functions receive a state and return a replacement state atomically,
    which makes states safe to compare, hash, replay, and store in search trees.
    """

    board: BoardState
    remaining_dice: tuple[DieId, ...] = DIE_ORDER
    current_player: int = 0
    leg_number: int = 1
    terminal: bool = False

    @classmethod
    def pre_setup(cls, track_length: int = 16) -> GameState:
        """Create a state awaiting seeded initial camel placement."""
        return cls(board=BoardState.empty(track_length))

    def __post_init__(self) -> None:
        """Validate canonical dice order and scalar state fields."""
        if len(self.remaining_dice) != len(set(self.remaining_dice)):
            raise ValueError("remaining_dice cannot contain duplicates")
        expected_order = tuple(die for die in DIE_ORDER if die in self.remaining_dice)
        if self.remaining_dice != expected_order:
            raise ValueError("remaining_dice must be valid and use canonical order")
        if self.current_player < 0:
            raise ValueError("current_player must be non-negative")
        if self.leg_number < 1:
            raise ValueError("leg_number must be positive")
        if not self.terminal and any(
            position.space in (-1, self.board.track_length)
            for position in self.board.camel_positions
        ):
            raise ValueError("a camel in a finish zone requires a terminal game")


def position_of(board: BoardState, camel: CamelId) -> CamelPosition:
    """Return the authoritative coordinate for ``camel``."""
    return board.camel_positions[_CAMEL_INDEX[camel]]


def stack_at(board: BoardState, space: int) -> tuple[CamelId, ...]:
    """Return the stack at ``space`` ordered from bottom to top."""
    if not -1 <= space <= board.track_length:
        raise ValueError("space must be on the track or in a finish zone")

    stack: list[tuple[int, CamelId]] = []
    for camel, position in zip(CAMEL_ORDER, board.camel_positions, strict=True):
        if position.space == space and position.level is not None:
            stack.append((position.level, camel))
    return tuple(camel for _, camel in sorted(stack))


def carried_camels(board: BoardState, camel: CamelId) -> tuple[CamelId, ...]:
    """Return ``camel`` and every camel above it, bottom to top."""
    position = position_of(board, camel)
    if position.space is None or position.level is None:
        raise ValueError("camel must be placed before it can carry a stack")
    return stack_at(board, position.space)[position.level :]
