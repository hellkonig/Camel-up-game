"""Typed state containers for the Camel Up engine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

STANDARD_DICE = ("red", "blue", "green", "yellow", "purple", "grey")


@dataclass
class Camel:
    """A camel and its current board position.

    ``stack_id`` is the camel's zero-based index in a board space. Index zero
    is the bottom of a stack and the last index is the top.
    """

    color: str
    block_id: int | None = None
    stack_id: int | None = None


@dataclass
class Board:
    """Mutable board state used by the prototype game loop.

    Each entry in ``blocks`` is ordered from the bottom of its camel stack to
    the top. Board methods mutate both the stacks and the position fields on
    affected camels so those two representations remain consistent.
    """

    land_len: int
    blocks: list[list[Camel]] = field(init=False)
    spectator_tiles: dict[int, str] = field(default_factory=dict, init=False)
    dices: list[str] = field(
        default_factory=lambda: list(STANDARD_DICE),
        init=False,
    )

    def __post_init__(self) -> None:
        """Create the requested number of empty board spaces."""
        self.blocks = [[] for _ in range(self.land_len)]

    def toss_dice(self) -> tuple[str, int]:
        """Remove and roll one of the dice still available this leg."""
        die_index = random.randint(0, len(self.dices) - 1)
        step = random.randint(1, 3)
        return self.dices.pop(die_index), step

    def place_camel(
        self,
        block_id: int,
        camels: list[Camel],
        forward: bool = True,
    ) -> None:
        """Place a camel stack on a space and update its positions.

        Forward-moving camels land on top of the existing stack. Backward-
        moving camels are placed underneath it. The order within ``camels`` is
        preserved in both cases.
        """
        if forward:
            self.blocks[block_id].extend(camels)
        else:
            self.blocks[block_id] = camels + self.blocks[block_id]

        self.update_camels(block_id)

    def update_camels(self, block_id: int) -> None:
        """Synchronize camel position fields for one board space."""
        for stack_id, camel in enumerate(self.blocks[block_id]):
            camel.block_id = block_id
            camel.stack_id = stack_id

    def select_camel(self, camel: Camel) -> list[Camel]:
        """Remove and return ``camel`` and every camel above it."""
        if camel.block_id is None or camel.stack_id is None:
            raise ValueError("camel must be placed before it can be selected")

        moving_stack = self.blocks[camel.block_id][camel.stack_id :]
        self.blocks[camel.block_id] = self.blocks[camel.block_id][: camel.stack_id]
        return moving_stack

    def place_spectator_tile(self, block_id: int, side: str) -> None:
        """Place a spectator tile when the prototype placement rules allow it."""
        if self.blocks[block_id]:
            print("Place your spectator tile into an empty space.")
        elif (
            block_id - 1 in self.spectator_tiles
            or block_id + 1 in self.spectator_tiles
        ):
            print(
                "You are not allowed to place the spectator tile"
                "onto a space that is adjacent to a space containing"
                "a spectator tile."
            )
        else:
            self.spectator_tiles[block_id] = side

    def one_leg_reset(self) -> None:
        """Restore the prototype state reset at the end of a leg."""
        self.spectator_tiles = {}
        self.dices[:] = STANDARD_DICE


@dataclass
class GameState:
    """State required to pause and continue a game.

    ``dice_inventory`` is the same mutable list exposed as ``board.dices``.
    Keeping one shared list preserves the prototype API while making ownership
    explicit at the game-state boundary.
    """

    board: Board
    camels: dict[str, Camel] = field(default_factory=dict)
    dice_inventory: list[str] = field(init=False)

    def __post_init__(self) -> None:
        """Link the game-level dice inventory to the compatibility board API."""
        self.dice_inventory = self.board.dices
