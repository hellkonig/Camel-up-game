"""Mutable prototype types retained until the CLI is migrated to engine APIs."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

LEGACY_DICE = ("red", "blue", "green", "yellow", "purple", "grey")


@dataclass
class Camel:
    """Camel representation expected by the prototype CLI."""

    color: str
    block_id: int | None = None
    stack_id: int | None = None


@dataclass
class Board:
    """Mutable board adapter expected by the prototype CLI."""

    land_len: int
    blocks: list[list[Camel]] = field(init=False)
    spectator_tiles: dict[int, str] = field(default_factory=dict, init=False)
    dices: list[str] = field(default_factory=lambda: list(LEGACY_DICE), init=False)

    def __post_init__(self) -> None:
        """Create the requested number of empty spaces."""
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
        """Place camels using the prototype's mutable stack behavior."""
        if forward:
            self.blocks[block_id].extend(camels)
        else:
            self.blocks[block_id] = camels + self.blocks[block_id]
        self.update_camels(block_id)

    def update_camels(self, block_id: int) -> None:
        """Synchronize prototype camel coordinates for one space."""
        for stack_id, camel in enumerate(self.blocks[block_id]):
            camel.block_id = block_id
            camel.stack_id = stack_id

    def select_camel(self, camel: Camel) -> list[Camel]:
        """Remove and return a camel and every camel above it."""
        if camel.block_id is None or camel.stack_id is None:
            raise ValueError("camel must be placed before it can be selected")
        moving_stack = self.blocks[camel.block_id][camel.stack_id :]
        self.blocks[camel.block_id] = self.blocks[camel.block_id][: camel.stack_id]
        return moving_stack

    def place_spectator_tile(self, block_id: int, side: str) -> None:
        """Place a tile using the prototype's terminal feedback behavior."""
        if self.blocks[block_id]:
            print("Place your spectator tile into an empty space.")
        elif (
            block_id - 1 in self.spectator_tiles or block_id + 1 in self.spectator_tiles
        ):
            print(
                "You are not allowed to place the spectator tile"
                "onto a space that is adjacent to a space containing"
                "a spectator tile."
            )
        else:
            self.spectator_tiles[block_id] = side

    def one_leg_reset(self) -> None:
        """Reset the prototype's leg-scoped state."""
        self.spectator_tiles = {}
        self.dices[:] = LEGACY_DICE
