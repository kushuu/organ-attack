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

        # card management
        self.card_manager = CardManager()
        self.effect_processor = CardEffectProcessor(self)

        # Game deck and discard pile
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []

        # Game state tracking
        self.active_effects: List[ActiveEffect] = []
        self.game_events: List[GameEvent] = []
        self.turn_count: int = 0
        self.winner: Optional[Player] = None

        # Temporary state for current turn
        self.current_attack: Optional[Dict[str, Any]] = None
        self.pending_defense: bool = False

        # Save management
        # TODO: implement save manager
        self.save_manager = None

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
        logger.info(f"Event: {event_type} by {player_name}")

    def _initialize_game(self):
        """Initialize the game with cards and starting hands."""
        logger.info("Initializing new game")

        # Build deck from non-organ cards
        all_cards = self.card_manager.get_all_non_organ_cards()

        # Create multiple copies of each card for balanced gameplay
        for card in all_cards:
            # Add 2-3 copies of each card depending on type
            copies = 5 if card.type.value in ['Attack', 'Defense'] else 2
            for _ in range(copies):
                self.deck.append(card)

        # Shuffle deck
        random.shuffle(self.deck)
        logger.info(f"Deck created with {len(self.deck)} cards")

        # Deal starting hands (5 cards each)
        for player in self.players:
            for _ in range(5):
                card = self._draw_card()
                if card:
                    player.add_card_to_hand(card)

        # Randomly select starting player
        self.current_player_index = random.randint(0, len(self.players) - 1)
        logger.info(f"Starting player: {self.get_current_player().name}")

        # Set initial game state
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
        return self.game_state == GameState.DONE
