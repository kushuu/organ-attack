"""
Core game engine for the Organ Attack card game.
Manages game state, turn flow, and card interactions.
"""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from game.cards import CardEffectProcessor, CardManager
from game.models import ActiveEffect, Card, CardType, GameEvent, GameState
from game.player import Player
from utils.save_manager import SaveManager

logger = logging.getLogger(__name__)


class GameEngine:
    """Main game engine that orchestrates gameplay."""

    def __init__(self, player_names: List[str]):
        if len(player_names) < 2 or len(player_names) > 4:
            raise ValueError("Game requires 2-4 players")

        self.players: List[Player] = [Player(name) for name in player_names]
        self.current_player_index: int = 0
        self.game_state: GameState = GameState.SETUP
        self.turn_direction: int = 1  # 1 = clockwise, -1 = counter-clockwise

        # Card management
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
        self.save_manager = SaveManager()

        self._initialize_game()

    def _initialize_game(self):
        """Initialize the game with cards and starting hands."""
        logger.info("Initializing new game")

        # Build deck from non-organ cards
        all_cards = self.card_manager.get_all_non_organ_cards()

        # Create multiple copies of each card for balanced gameplay
        for card in all_cards:
            # Add 2-3 copies of each card depending on type
            copies = 3 if card.type.value in ['Attack', 'Defense'] else 2
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
        self.game_state = GameState.DRAW

        self._log_event("game_start", "System", details={
            'players': [p.name for p in self.players],
            'starting_player': self.get_current_player().name
        })

    def get_current_player(self) -> Player:
        """Get the currently active player."""
        return self.players[self.current_player_index]

    def get_active_players(self) -> List[Player]:
        """Get all players who are still in the game."""
        return [p for p in self.players if not p.is_eliminated()]

    def get_other_players(self, exclude_player: Player) -> List[Player]:
        """Get all other active players except the specified one."""
        return [p for p in self.get_active_players() if p != exclude_player]

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

    def draw_card_for_player(self, player: Player) -> Optional[Card]:
        """Draw a card for a specific player."""
        card = self._draw_card()
        if card:
            player.add_card_to_hand(card)
            player.cards_drawn_this_turn += 1
        return card

    def _discard_card(self, card: Card):
        """Add a card to the discard pile."""
        self.discard_pile.append(card)

    def can_play_card(self, player: Player, card: Card, target_player: Optional[Player] = None,
                      target_organ: Optional[str] = None) -> Tuple[bool, str]:
        """Check if a player can play a specific card."""
        if card not in player.hand:
            return False, "Card not in hand"

        # Check game state restrictions
        if self.game_state == GameState.DEFEND and card.type.value != 'Defense':
            return False, "Can only play defense cards during defend phase"

        if self.game_state not in [GameState.PLAY, GameState.DEFEND]:
            return False, f"Cannot play cards during {self.game_state.name} phase"

        # Validate card conditions
        valid, message = self.card_manager.validate_card_play(card, self)
        if not valid:
            return False, message

        # Check targeting
        if card.target:
            if card.target.organ_type and target_organ != card.target.organ_type:
                return False, f"Card must target {card.target.organ_type}"

            if card.target.player_scope == "Other" and target_player == player:
                return False, "Cannot target yourself with this card"

            if target_player and target_organ:
                if not target_player.has_organ(target_organ):
                    return False, f"Target player doesn't have {target_organ}"

        return True, "Valid"

    def play_card(self, player: Player, card: Card, target_player: Optional[Player] = None,
                  target_organ: Optional[str] = None) -> Dict[str, Any]:
        """Play a card with the specified targets."""
        # Validate the play
        logger.info(f"Player {player.name} playing {card.name}")
        can_play, reason = self.can_play_card(
            player, card, target_player, target_organ)
        if not can_play:
            return {
                'success': False,
                'reason': reason,
                'card': card.name
            }

        # Remove card from player's hand
        player.remove_card_from_hand(card)
        player.cards_played_this_turn += 1

        # Log the play
        self._log_event("card_played", player.name,
                        card_played=card.name,
                        target_player=target_player.name if target_player else None,
                        target_organ=target_organ)

        # Handle different card types
        if card.type.value == 'Attack':
            return self._handle_attack_card(card, player, target_player, target_organ)
        elif card.type.value == 'Defense':
            return self._handle_defense_card(card, player)
        elif card.type.value == 'Action':
            return self._handle_action_card(card, player, target_player, target_organ)
        elif card.type.value == 'Wildcard':
            return self._handle_wildcard_card(card, player, target_player, target_organ)
        else:
            # Process effects directly for other card types
            results = self.effect_processor.process_card_effects(
                card, player, target_player, target_organ
            )
            self._discard_card(card)
            return {
                'success': True,
                'card': card.name,
                'effects': results
            }

    def _handle_attack_card(self, card: Card, attacker: Player, target_player: Player,
                            target_organ: str) -> Dict[str, Any]:
        """Handle playing an attack card."""
        if not target_player or not target_organ:
            return {
                'success': False,
                'reason': 'Attack cards require target player and organ',
                'card': card.name
            }

        # Set up attack for potential defense
        self.current_attack = {
            'card': card,
            'attacker': attacker,
            'target_player': target_player,
            'target_organ': target_organ
        }

        # Check if target can defend
        defense_cards = target_player.get_cards_by_type(CardType.DEFENSE)
        if defense_cards:
            self.pending_defense = True
            self.game_state = GameState.DEFEND
            return {
                'success': True,
                'card': card.name,
                'awaiting_defense': True,
                'target_player': target_player.name,
                'target_organ': target_organ
            }
        else:
            # No defense possible, resolve attack immediately
            return self._resolve_attack()

    def _handle_defense_card(self, card: Card, defender: Player) -> Dict[str, Any]:
        """Handle playing a defense card."""
        if not self.current_attack or not self.pending_defense:
            return {
                'success': False,
                'reason': 'No attack to defend against',
                'card': card.name
            }

        # Process defense
        self._discard_card(card)
        self.pending_defense = False
        attack_card = self.current_attack['card']
        attacker = self.current_attack['attacker']

        # Log successful defense
        self._log_event("attack_defended", defender.name,
                        card_played=card.name,
                        details={'blocked_attack': attack_card.name,
                                 'attacker': attacker.name})

        # Discard the blocked attack card
        self._discard_card(attack_card)
        self.current_attack = None
        self.game_state = GameState.DISCARD

        return {
            'success': True,
            'card': card.name,
            'blocked_attack': attack_card.name,
            'message': f"{card.name} blocked {attack_card.name}!"
        }

    def _handle_action_card(self, card: Card, player: Player, target_player: Optional[Player],
                            target_organ: Optional[str]) -> Dict[str, Any]:
        """Handle playing an action card."""
        results = self.effect_processor.process_card_effects(
            card, player, target_player, target_organ
        )
        self._discard_card(card)

        return {
            'success': True,
            'card': card.name,
            'effects': results
        }

    def _handle_wildcard_card(self, card: Card, player: Player, target_player: Optional[Player],
                              target_organ: Optional[str]) -> Dict[str, Any]:
        """Handle playing a wildcard card."""
        # Wildcards require special handling based on player choice
        # For now, treat as action card
        return self._handle_action_card(card, player, target_player, target_organ)

    def _resolve_attack(self) -> Dict[str, Any]:
        """Resolve an attack that wasn't defended."""
        if not self.current_attack:
            return {'success': False, 'reason': 'No attack to resolve'}

        attack_card = self.current_attack['card']
        attacker = self.current_attack['attacker']
        target_player = self.current_attack['target_player']
        target_organ = self.current_attack['target_organ']

        # Process attack effects
        results = self.effect_processor.process_card_effects(
            attack_card, attacker, target_player, target_organ
        )

        # Discard attack card
        self._discard_card(attack_card)
        self.current_attack = None
        self.pending_defense = False
        self.game_state = GameState.DISCARD

        return {
            'success': True,
            'card': attack_card.name,
            'target_player': target_player.name,
            'target_organ': target_organ,
            'effects': results
        }

    def skip_defense(self) -> Dict[str, Any]:
        """Skip defense phase and resolve the attack."""
        if not self.pending_defense:
            return {'success': False, 'reason': 'No defense to skip'}

        return self._resolve_attack()

    def advance_turn(self):
        """Advance to the next turn phase or next player."""
        current_player = self.get_current_player()

        if self.game_state == GameState.DRAW:
            # Draw phase - draw a card
            if current_player.cards_drawn_this_turn == 0:
                self.draw_card_for_player(current_player)
            self.game_state = GameState.PLAY

        elif self.game_state == GameState.PLAY:
            # Play phase completed, move to discard
            self.game_state = GameState.DISCARD

        elif self.game_state == GameState.DEFEND:
            # Defense phase - waiting for player input
            pass

        elif self.game_state == GameState.DISCARD:
            # Handle discarding if necessary
            if current_player.needs_to_discard():
                # Player needs to choose cards to discard
                return
            self.game_state = GameState.NEXT_TURN

        elif self.game_state == GameState.NEXT_TURN:
            # Move to next player
            self._next_player()
            self.game_state = GameState.DRAW

        # Check win condition
        self._check_win_condition()

    def _next_player(self):
        """Move to the next active player."""
        current_player = self.get_current_player()
        current_player.reset_turn_counters()

        # Find next active player
        attempts = 0
        while attempts < len(self.players):
            self.current_player_index = (
                self.current_player_index + self.turn_direction
            ) % len(self.players)

            next_player = self.get_current_player()
            if not next_player.is_eliminated():
                if next_player.skip_next_turn:
                    next_player.skip_next_turn = False
                    self._log_event("turn_skipped", next_player.name)
                else:
                    break

            attempts += 1

        self.turn_count += 1
        logger.info(
            f"Turn {self.turn_count}: {self.get_current_player().name}")

    def force_discard(self, player: Player, cards_to_discard: List[Card]) -> bool:
        """Force a player to discard specific cards."""
        for card in cards_to_discard:
            if card in player.hand:
                player.hand.remove(card)
                self._discard_card(card)

        return not player.needs_to_discard()

    def _check_win_condition(self) -> bool:
        """Check if the game has ended."""
        active_players = self.get_active_players()

        if len(active_players) <= 1:
            self.game_state = GameState.GAME_OVER
            if active_players:
                self.winner = active_players[0]
                logger.info(f"Game over! Winner: {self.winner.name}")
                self._log_event("game_end", "System",
                                details={'winner': self.winner.name,
                                         'total_turns': self.turn_count})
            else:
                logger.info("Game over! No winner (all players eliminated)")
                self._log_event("game_end", "System",
                                details={'winner': None, 'total_turns': self.turn_count})
            return True

        return False

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return self.game_state == GameState.GAME_OVER

    def get_winner(self) -> Optional[Player]:
        """Get the winner of the game."""
        return self.winner

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

    def get_game_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current game state."""
        current_player = self.get_current_player()

        return {
            'game_state': self.game_state.name,
            'turn_count': self.turn_count,
            'current_player': current_player.name,
            'current_player_index': self.current_player_index,
            'players': [p.get_status_summary() for p in self.players],
            'deck_size': len(self.deck),
            'discard_size': len(self.discard_pile),
            'pending_defense': self.pending_defense,
            'current_attack': {
                'attacker': self.current_attack['attacker'].name,
                'target_player': self.current_attack['target_player'].name,
                'target_organ': self.current_attack['target_organ'],
                'card': self.current_attack['card'].name
            } if self.current_attack else None,
            'winner': self.winner.name if self.winner else None,
            'is_game_over': self.is_game_over()
        }

    def save_game(self, filename: str) -> bool:
        """Save the current game state."""
        try:
            game_data = {
                'players': [
                    {
                        'name': p.name,
                        'organs': {k: {
                            'id': v.id,
                            'name': v.name,
                            'is_removed': v.is_removed,
                            'is_protected': v.is_protected,
                            'protection_source': v.protection_source
                        } for k, v in p.organs.items()},
                        'hand': [{'id': card.id, 'name': card.name} for card in p.hand],
                        'status': p.status.value,
                        'skip_next_turn': p.skip_next_turn
                    } for p in self.players
                ],
                'current_player_index': self.current_player_index,
                'game_state': self.game_state.name,
                'turn_direction': self.turn_direction,
                'turn_count': self.turn_count,
                'deck_size': len(self.deck),
                'discard_size': len(self.discard_pile),
                'game_events': [
                    {
                        'event_type': e.event_type,
                        'player_name': e.player_name,
                        'card_played': e.card_played,
                        'target_player': e.target_player,
                        'target_organ': e.target_organ,
                        'success': e.success,
                        'details': e.details
                    } for e in self.game_events
                ]
            }

            return self.save_manager.save_game(filename, game_data)
        except Exception as e:
            logger.error(f"Error saving game: {e}")
            return False

    def load_game(self, filename: str) -> bool:
        """Load a saved game state."""
        try:
            game_data = self.save_manager.load_game(filename)
            if not game_data:
                return False

            # Reconstruct game state from saved data
            # This is a simplified version - full implementation would reconstruct all objects
            self.current_player_index = game_data['current_player_index']
            self.game_state = GameState[game_data['game_state']]
            self.turn_direction = game_data['turn_direction']
            self.turn_count = game_data['turn_count']

            logger.info(f"Game loaded from {filename}")
            return True

        except Exception as e:
            logger.error(f"Error loading game: {e}")
            return False
