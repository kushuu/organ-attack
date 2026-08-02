import copy
import logging
import random
from typing import Any, Dict, List, Optional

from game.cards import CardEffectProcessor, CardManager
from game.models import ActiveEffect, Card, GameEvent, GameState, TurnDirection
from game.player import Player

logger = logging.getLogger(__name__)


class GameEngine:
    def __init__(self, player_names: list[str]):
        self.player_names = player_names
        self.current_player_index = 0
        self.players = [Player(name) for name in player_names]
        self.turn_direction = TurnDirection.CLOCKWISE

        self.card_manager = CardManager()
        self.effect_processor = CardEffectProcessor(self)

        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []

        self.active_effects: List[ActiveEffect] = []
        self.game_events: List[GameEvent] = []
        self.turn_count: int = 0
        self.winner: Optional[Player] = None

        self.current_attack: Optional[Dict[str, Any]] = None
        self.pending_defense: bool = False

        self.save_manager = None
        self.game_state = GameState.PLAY

        self._initialize_game()

    def _draw_card(self) -> Optional[Card]:
        """Draw a card from the deck."""
        if not self.deck:
            self._reshuffle_deck()

        if self.deck:
            return self.deck.pop()
        return None

    def _reshuffle_deck(self):
        """Reshuffle discard pile into deck when deck is empty."""
        if self.discard_pile:
            logger.info("Reshuffling discard pile into deck")
            self.deck = self.discard_pile.copy()
            self.discard_pile.clear()
            random.shuffle(self.deck)

    def get_current_player(self) -> Player:
        return self.players[self.current_player_index]

    def get_other_players(self, current_player):
        """Return a list of all players except the current player."""
        return [p for p in self.players if p != current_player]

    def get_active_players(self):
        """Return a list of all players who are not eliminated."""
        return [p for p in self.players if not p.is_eliminated()]

    def _log_event(self, event_type: str, player_name: str, card_played: Optional[str] = None,
                   target_player: Optional[str] = None, target_organ: Optional[str] = None,
                   success: bool = True, details: Optional[Dict[str, Any]] = None):
        """Log a game event."""
        event = GameEvent(
            event_type=event_type,
            player_name=player_name,
            card_played=card_played,
            target_player=target_player,
            target_organ=target_organ,
            success=success,
            details=details or {}
        )
        self.game_events.append(event)

    def _initialize_game(self):
        """Initialize the game with cards and starting hands."""
        logger.info("Initializing new game")

        all_cards = self.card_manager.get_all_non_organ_cards()

        # Create DEEP COPIES of each card to avoid shared references
        for card in all_cards:
            copies = 5 if card.type.value in ['Attack', 'Defense'] else 2
            for _ in range(copies):
                self.deck.append(copy.deepcopy(card))

        random.shuffle(self.deck)
        logger.info(f"Deck created with {len(self.deck)} cards")

        # Deal starting hands (5 cards each)
        for player in self.players:
            for _ in range(5):
                card = self._draw_card()
                if card:
                    player.add_card_to_hand(card)

        self.current_player_index = random.randint(0, len(self.players) - 1)
        logger.info(f"Starting player: {self.get_current_player().name}")

        self.game_state = GameState.PLAY

        self._log_event("game_start", "System", details={
            'players': [p.name for p in self.players],
            'starting_player': self.get_current_player().name
        })

    def draw_card_for_player(self, player: Player) -> Optional[Card]:
        """Draw a card for a specific player."""
        card = self._draw_card()
        if card:
            player.add_card_to_hand(card)
            player.cards_drawn_this_turn += 1
        return card

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        if self.game_state == GameState.DONE:
            return True
        active = self.get_active_players()
        return len(active) <= 1

    def to_dict(self) -> dict:
        """Convert game state to dictionary for network transmission."""
        players_data = []
        for p in self.players:
            try:
                players_data.append(p.to_dict())
            except Exception as e:
                logger.error(f"Error serializing player {p.name}: {e}")
                players_data.append({
                    "name": p.name,
                    "organs": {},
                    "hand": [],
                    "status": p.status.value,
                    "cards_played_this_turn": 0,
                    "cards_drawn_this_turn": 0,
                    "can_draw_extra": False,
                    "skip_next_turn": False
                })

        discard_data = []
        for card in self.discard_pile:
            try:
                discard_data.append({
                    "id": card.id,
                    "name": card.name,
                    "type": card.type.value if card.type else "Unknown",
                    "description": card.description or "",
                    "organ_type": card.organ_type
                })
            except Exception:
                discard_data.append({
                    "id": getattr(card, 'id', '?'),
                    "name": getattr(card, 'name', '?'),
                    "type": "Unknown",
                    "description": "",
                    "organ_type": None
                })

        return {
            "player_names": self.player_names,
            "current_player_index": self.current_player_index,
            "turn_direction": self.turn_direction.value,
            "players": players_data,
            "turn_count": self.turn_count,
            "game_state": self.game_state.value,
            "deck_size": len(self.deck),
            "discard_pile": discard_data
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameEngine":
        """Create game engine from dictionary. Used for client-side rendering."""
        player_names = data.get("player_names", [])
        engine = cls(player_names)

        engine.current_player_index = data.get("current_player_index", 0)
        engine.turn_direction = TurnDirection(data.get("turn_direction", 1))
        engine.turn_count = data.get("turn_count", 0)

        gs = data.get("game_state", 1)
        try:
            engine.game_state = GameState(gs)
        except (ValueError, TypeError):
            engine.game_state = GameState.PLAY

        # Restore players from dict
        engine.players = []
        for p_data in data.get("players", []):
            player = Player.from_dict(p_data)
            engine.players.append(player)

        # Rebuild deck (deck is not transmitted, just rebuild from card manager)
        engine.deck = []
        engine.discard_pile = []

        engine.active_effects = []
        engine.game_events = []
        engine.winner = None
        engine.current_attack = None
        engine.pending_defense = False

        return engine
