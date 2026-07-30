"""Temporary compatibility imports for the prototype CLI.

New code should import these types from :mod:`camel_up.engine`.
"""

from camel_up.engine import Board, Camel, GameState

__all__ = ["Board", "Camel", "GameState"]
