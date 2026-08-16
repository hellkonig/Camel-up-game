"""Stable public types and queries for the Camel Up engine."""

from camel_up.engine.dice import (
    DieRoll,
    SetupRoll,
    reset_leg_dice,
    roll_die,
    setup_game,
)
from camel_up.engine.movement import move_camel
from camel_up.engine.state import (
    CAMEL_ORDER,
    DIE_ORDER,
    BoardState,
    CamelId,
    CamelPosition,
    DieId,
    GameState,
    SpectatorTile,
    carried_camels,
    position_of,
    stack_at,
)

__all__ = [
    "CAMEL_ORDER",
    "DIE_ORDER",
    "BoardState",
    "CamelId",
    "CamelPosition",
    "DieId",
    "DieRoll",
    "GameState",
    "SpectatorTile",
    "SetupRoll",
    "carried_camels",
    "move_camel",
    "position_of",
    "reset_leg_dice",
    "roll_die",
    "setup_game",
    "stack_at",
]
