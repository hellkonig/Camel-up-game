"""Canonical, immutable state containers for the Camel Up engine."""

from __future__ import annotations

from collections.abc import Iterable
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


class FinalBetTarget(str, Enum):
    """The final betting record that receives a finish card."""

    WINNER = "winner"
    LOSER = "loser"


# Stable identity/serialization order; this is unrelated to current race ranking.
RACING_CAMEL_ORDER: Final = (
    CamelId.RED,
    CamelId.BLUE,
    CamelId.GREEN,
    CamelId.YELLOW,
    CamelId.PURPLE,
)
CAMEL_ORDER: Final = (*RACING_CAMEL_ORDER, CamelId.WHITE, CamelId.BLACK)
DIE_ORDER: Final = tuple(DieId)
MIN_PLAYERS: Final = 3
MAX_PLAYERS: Final = 8
# Each stack is stored from bottom to top so its available ticket is last.
LEG_BETTING_TICKET_STACK_VALUES: Final = (2, 2, 3, 5)
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
    """A placed spectator tile's owner, location, and movement effect.

    This type records canonical tile state. Tile-placement actions, landing
    effects, owner rewards, and leg resets belong to later rule transitions.
    """

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
class LegBettingTicket:
    """A leg-scoped betting ticket held by one player.

    Attributes:
        camel: The racing camel backed by the ticket.
        value: The ticket's printed payout when its camel leads the leg.
    """

    camel: CamelId
    value: int

    def __post_init__(self) -> None:
        """Require a printed ticket from the racing-camel supply."""
        if self.camel not in RACING_CAMEL_ORDER:
            raise ValueError("leg betting tickets must show a racing camel")
        if self.value not in LEG_BETTING_TICKET_STACK_VALUES:
            raise ValueError("leg betting ticket value must be 2, 3, or 5")


@dataclass(frozen=True, slots=True)
class FinalBet:
    """One finish card placed into an ordered final betting record.

    The containing winner or loser tuple determines what the card predicts, so
    the target is not duplicated on each record.

    The record can reject negative player IDs independently. The containing
    :class:`GameState` validates the upper bound against its actual player
    roster.

    Attributes:
        player_id: Stable identity of the player who placed the finish card.
        camel: Racing camel predicted to finish first or last.
    """

    player_id: int
    camel: CamelId

    def __post_init__(self) -> None:
        """Require a possible player identity and racing-camel prediction."""
        if self.player_id < 0:
            raise ValueError("player_id must be non-negative")
        if self.camel not in RACING_CAMEL_ORDER:
            raise ValueError("final bets must predict a racing camel")


def _leg_betting_ticket_sort_key(
    ticket: LegBettingTicket,
) -> tuple[int, int]:
    """Order by ``RACING_CAMEL_ORDER``, then by descending ticket value."""
    return _CAMEL_INDEX[ticket.camel], -ticket.value


def canonical_leg_betting_tickets(
    tickets: Iterable[LegBettingTicket],
) -> tuple[LegBettingTicket, ...]:
    """Return leg tickets in the canonical player-holdings order."""
    return tuple(sorted(tickets, key=_leg_betting_ticket_sort_key))


def _finish_card_sort_key(card: tuple[int, CamelId]) -> tuple[int, int]:
    """Order a finish card by player identity, then racing camel identity."""
    player_id, camel = card
    return player_id, _CAMEL_INDEX[camel]


INITIAL_LEG_BETTING_TICKET_STACKS: Final = tuple(
    tuple(
        LegBettingTicket(camel=camel, value=value)
        for value in LEG_BETTING_TICKET_STACK_VALUES
    )
    for camel in RACING_CAMEL_ORDER
)
_ALL_LEG_BETTING_TICKETS: Final = canonical_leg_betting_tickets(
    ticket for stack in INITIAL_LEG_BETTING_TICKET_STACKS for ticket in stack
)


@dataclass(frozen=True, slots=True)
class PlayerState:
    """Authoritative player-owned data for one engine state.

    This is complete engine truth, not a player-relative RL observation.
    Observation encoders must mask information an observing player cannot
    legally know, including opponents' available finish cards.

    Leg betting tickets are canonicalized by racing-camel identity order (red,
    blue, green, yellow, purple) and then by descending printed value. This
    order is unrelated to race ranking. Available finish cards form a canonical
    subsequence of :data:`RACING_CAMEL_ORDER`. Requiring these orders gives
    logically equivalent holdings identical equality and hashing behavior.

    Attributes:
        player_id: Stable seat index, beginning at zero.
        money: Egyptian Pounds currently owned by the player.
        pyramid_ticket_count: Leg-scoped pyramid tickets collected by rolling;
            each is worth one Egyptian Pound during leg scoring.
        leg_betting_tickets: Leg-scoped betting tickets currently held, ordered
            by camel and then by descending printed value.
        available_finish_cards: Secret finish cards the player has not played.
    """

    player_id: int
    money: int = 3
    pyramid_ticket_count: int = 0
    leg_betting_tickets: tuple[LegBettingTicket, ...] = ()
    available_finish_cards: tuple[CamelId, ...] = RACING_CAMEL_ORDER

    def __post_init__(self) -> None:
        """Validate scalar resources and canonical player-owned collections."""
        if self.player_id < 0:
            raise ValueError("player_id must be non-negative")
        if self.money < 0:
            raise ValueError("money must be non-negative")
        if self.pyramid_ticket_count < 0:
            raise ValueError("pyramid_ticket_count must be non-negative")

        expected_tickets = canonical_leg_betting_tickets(self.leg_betting_tickets)
        if self.leg_betting_tickets != expected_tickets:
            raise ValueError("leg_betting_tickets must use canonical order")

        expected_cards = tuple(
            camel
            for camel in RACING_CAMEL_ORDER
            if camel in self.available_finish_cards
        )
        if self.available_finish_cards != expected_cards:
            raise ValueError(
                "available_finish_cards must contain unique racing camels "
                "in canonical order"
            )


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
    """Authoritative state foundation for deterministic engine transitions.

    The state contains no random generator and exposes no mutation methods.
    Rule functions receive a state and return a replacement state atomically,
    which makes states safe to compare, hash, replay, and store in search trees.
    It contains complete game truth; agents must consume a future
    player-relative observation rather than this state directly when the rules
    require hidden information.

    Shared ticket supplies and ordered final betting records live here, while
    held tickets and unused finish cards live on their owning
    :class:`PlayerState`. Construction validates that those locations conserve
    every betting asset.
    """

    board: BoardState
    players: tuple[PlayerState, ...]
    remaining_dice: tuple[DieId, ...] = DIE_ORDER
    current_player: int = 0
    leg_number: int = 1
    terminal: bool = False
    available_leg_betting_tickets: tuple[tuple[LegBettingTicket, ...], ...] = (
        INITIAL_LEG_BETTING_TICKET_STACKS
    )
    final_winner_bets: tuple[FinalBet, ...] = ()
    final_loser_bets: tuple[FinalBet, ...] = ()

    @classmethod
    def pre_setup(
        cls,
        track_length: int = 16,
        player_count: int = MIN_PLAYERS,
    ) -> GameState:
        """Create a game with players that awaits initial camel placement."""
        players = tuple(PlayerState(player_id=index) for index in range(player_count))
        return cls(board=BoardState.empty(track_length), players=players)

    def __post_init__(self) -> None:
        """Validate player ownership, canonical dice, and scalar state fields."""
        if not MIN_PLAYERS <= len(self.players) <= MAX_PLAYERS:
            raise ValueError(
                f"players must contain between {MIN_PLAYERS} and {MAX_PLAYERS} entries"
            )
        player_ids = tuple(player.player_id for player in self.players)
        if player_ids != tuple(range(len(self.players))):
            raise ValueError(
                "players must be ordered by contiguous player_id values from zero"
            )
        if not 0 <= self.current_player < len(self.players):
            raise ValueError("current_player must identify a player in players")
        if any(
            tile.player_id >= len(self.players) for tile in self.board.spectator_tiles
        ):
            raise ValueError("spectator tiles must belong to a player in players")
        self._validate_leg_betting_assets()
        self._validate_finish_card_assets()
        if len(self.remaining_dice) != len(set(self.remaining_dice)):
            raise ValueError("remaining_dice cannot contain duplicates")
        expected_order = tuple(die for die in DIE_ORDER if die in self.remaining_dice)
        if self.remaining_dice != expected_order:
            raise ValueError("remaining_dice must be valid and use canonical order")
        if self.leg_number < 1:
            raise ValueError("leg_number must be positive")
        if not self.terminal and any(
            position.space in (-1, self.board.track_length)
            for position in self.board.camel_positions
        ):
            raise ValueError("a camel in a finish zone requires a terminal game")

    def _validate_leg_betting_assets(self) -> None:
        """Require canonical stacks and conserve every leg betting ticket."""
        if len(self.available_leg_betting_tickets) != len(RACING_CAMEL_ORDER):
            raise ValueError("available_leg_betting_tickets must use canonical order")

        for available_stack, initial_stack in zip(
            self.available_leg_betting_tickets,
            INITIAL_LEG_BETTING_TICKET_STACKS,
            strict=True,
        ):
            if available_stack != initial_stack[: len(available_stack)]:
                raise ValueError(
                    "available_leg_betting_tickets must use canonical stacks"
                )

        held_tickets = tuple(
            ticket for player in self.players for ticket in player.leg_betting_tickets
        )
        available_tickets = tuple(
            ticket for stack in self.available_leg_betting_tickets for ticket in stack
        )
        all_leg_tickets = canonical_leg_betting_tickets(
            (*available_tickets, *held_tickets)
        )
        if all_leg_tickets != _ALL_LEG_BETTING_TICKETS:
            raise ValueError(
                "available and held leg betting tickets must conserve the "
                "initial supply"
            )

    def _validate_finish_card_assets(self) -> None:
        """Conserve finish cards across players and final betting records."""
        all_finish_cards = [
            (player.player_id, camel)
            for player in self.players
            for camel in player.available_finish_cards
        ]
        for bet in (*self.final_winner_bets, *self.final_loser_bets):
            if bet.player_id >= len(self.players):
                raise ValueError("final bets must belong to a player in players")
            all_finish_cards.append((bet.player_id, bet.camel))

        expected_finish_cards = tuple(
            (player.player_id, camel)
            for player in self.players
            for camel in RACING_CAMEL_ORDER
        )
        ordered_finish_cards = tuple(
            sorted(
                all_finish_cards,
                key=_finish_card_sort_key,
            )
        )
        if ordered_finish_cards != expected_finish_cards:
            raise ValueError(
                "available finish cards and final bets must conserve one card "
                "per player and racing camel"
            )


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


def spectator_tile_for_player(
    state: GameState,
    player_id: int,
) -> SpectatorTile | None:
    """Return a player's placed tile, or ``None`` when it is available."""
    if not 0 <= player_id < len(state.players):
        raise ValueError("player_id must identify a player in players")
    return next(
        (tile for tile in state.board.spectator_tiles if tile.player_id == player_id),
        None,
    )
