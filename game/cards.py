"""
Card management and effects system for the Organ Attack card game.
Handles card loading, validation, and effect execution.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from game.models import (Card, CardConditions, CardEffect, CardTarget,
                         CardType, OrganCard)
from game.player import Player

logger = logging.getLogger(__name__)


class CardManager:
    """Manages all cards in the game including loading and validation."""

    def __init__(self, cards_file: str = "data/cards.json"):
        self.cards_file = cards_file
        self.all_cards: Dict[str, Card] = {}
        self.cards_by_type: Dict[CardType, List[Card]] = {
            card_type: [] for card_type in CardType
        }
        self.load_cards()

    def load_cards(self):
        """Load cards from JSON file."""
        try:
            cards_path = Path(self.cards_file)
            if not cards_path.exists():
                logger.error(f"Cards file not found: {self.cards_file}")
                self._create_default_cards()
                return

            with open(cards_path, 'r') as f:
                cards_data = json.load(f)

            self._parse_cards(cards_data)
            logger.info(
                f"Loaded {len(self.all_cards)} cards from {self.cards_file}")

        except Exception as e:
            logger.error(f"Error loading cards: {e}")
            self._create_default_cards()

    def _parse_cards(self, cards_data: Dict[str, Any]):
        """Parse cards from JSON data."""
        for card_data in cards_data.get('cards', []):
            try:
                card = self._create_card_from_data(card_data)
                self.all_cards[card.id] = card

                # Categorize by type
                card_type = CardType(card.type.value)
                self.cards_by_type[card_type].append(card)

            except Exception as e:
                logger.error(
                    f"Error parsing card {card_data.get('id', 'unknown')}: {e}")

    def _create_card_from_data(self, data: Dict[str, Any]) -> Card:
        """Create a Card object from JSON data."""
        # Parse target information
        target = None
        if 'target' in data and data['target']:
            target_data = data['target']
            target = CardTarget(
                organ_type=target_data.get('organ_type'),
                scope=target_data.get('scope', 'Single'),
                player_scope=target_data.get('player_scope', 'Other'),
                organ_scope=target_data.get('organ_scope', 'Single'),
                flexible=target_data.get('flexible', False)
            )

        # Parse conditions
        conditions = None
        if 'conditions' in data and data['conditions']:
            cond_data = data['conditions']
            conditions = CardConditions(
                organ_must_be_present=cond_data.get(
                    'organ_must_be_present', False),
                organ_must_not_be_protected=cond_data.get(
                    'organ_must_not_be_protected', False),
                target_organ_must_be_present=cond_data.get(
                    'target_organ_must_be_present', False),
                player_must_have_available_slot=cond_data.get(
                    'player_must_have_available_slot', False),
                must_be_played_in_response_or_attack_phase=cond_data.get(
                    'must_be_played_in_response_or_attack_phase', False)
            )

        # Parse effects
        effects = []
        for effect_data in data.get('effects', []):
            effect = CardEffect(
                action=effect_data['action'],
                target_organ=effect_data.get('target_organ'),
                duration=effect_data.get('duration', 'instant'),
                value=effect_data.get('value'),
                mimic_type=effect_data.get('mimic_type'),
                from_target=effect_data.get('from'),
                to_target=effect_data.get('to')
            )
            effects.append(effect)

        # Create card
        card_type = CardType(data['type'])

        if card_type == CardType.ORGAN:
            # Special handling for organ cards
            return OrganCard(
                id=data['id'],
                name=data['name'],
                type=card_type,
                description=data['description'],
                target=target,
                conditions=conditions,
                effects=effects,
                organ_type=data.get('organ_type'),
                is_vital=data.get('is_vital', False),
                can_be_protected=data.get('can_be_protected', True)
            )
        else:
            return Card(
                id=data['id'],
                name=data['name'],
                type=card_type,
                description=data['description'],
                target=target,
                conditions=conditions,
                effects=effects,
                organ_type=data.get('organ_type'),
                is_vital=data.get('is_vital', False),
                can_be_protected=data.get('can_be_protected', True)
            )

    def _create_default_cards(self):
        """Create a basic set of cards if JSON loading fails."""
        logger.warning("Creating default card set")

        # Create some basic attack cards
        basic_attacks = [
            {
                'id': 'attack_001',
                'name': 'Heart Attack',
                'type': 'Attack',
                'description': 'Attack the heart organ.',
                'target': {'organ_type': 'Heart'},
                'effects': [{'action': 'remove_organ', 'target_organ': 'Heart'}]
            },
            {
                'id': 'attack_002',
                'name': 'Brain Freeze',
                'type': 'Attack',
                'description': 'Attack the brain organ.',
                'target': {'organ_type': 'Brain'},
                'effects': [{'action': 'remove_organ', 'target_organ': 'Brain'}]
            }
        ]

        # Create some basic defense cards
        basic_defenses = [
            {
                'id': 'defense_001',
                'name': 'Medical Kit',
                'type': 'Defense',
                'description': 'Block any attack.',
                'effects': [{'action': 'block_attack'}]
            }
        ]

        # Parse default cards
        default_data = {'cards': basic_attacks + basic_defenses}
        self._parse_cards(default_data)

    def get_card(self, card_id: str) -> Optional[Card]:
        """Get a card by ID."""
        return self.all_cards.get(card_id)

    def get_cards_by_type(self, card_type: CardType) -> List[Card]:
        """Get all cards of a specific type."""
        return self.cards_by_type.get(card_type, [])

    def get_all_non_organ_cards(self) -> List[Card]:
        """Get all cards except organ cards for deck building."""
        non_organ_cards = []
        for card_type in CardType:
            if card_type != CardType.ORGAN:
                non_organ_cards.extend(self.cards_by_type[card_type])
        return non_organ_cards

    def validate_card_play(self, card: Card, game_state: Any) -> tuple[bool, str]:
        """Validate if a card can be played in the current game state."""
        try:
            # Basic validation
            if not card:
                return False, "Invalid card"

            if not card.conditions:
                return True, "Valid"

            # Check specific conditions
            conditions = card.conditions

            # Add more validation logic based on game state
            # This is a simplified version
            return True, "Valid"

        except Exception as e:
            logger.error(f"Error validating card play: {e}")
            return False, f"Validation error: {e}"


class CardEffectProcessor:
    """Processes card effects during gameplay."""

    def __init__(self, game_engine):
        self.game_engine = game_engine

    def process_card_effects(self, card: Card, player, target_player=None, target_organ=None):
        """Process all effects of a played card."""
        results = []

        for effect in card.effects:
            try:
                result = self._process_single_effect(
                    effect, card, player, target_player, target_organ
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing effect {effect.action}: {e}")
                results.append({'success': False, 'error': str(e)})

        return results

    def _process_single_effect(self, effect: CardEffect, card: Card, player, target_player=None, target_organ=None):
        """Process a single card effect."""
        action = effect.action

        if action == 'remove_organ':
            return self._remove_organ_effect(effect, player, target_player, target_organ)
        elif action == 'protect_organ':
            return self._protect_organ_effect(effect, player, target_player, target_organ, card)
        elif action == 'block_attack':
            return self._block_attack_effect(effect, player)
        elif action == 'steal_organ':
            return self._steal_organ_effect(effect, player, target_player, target_organ)
        elif action == 'draw_cards':
            return self._draw_cards_effect(effect, player)
        elif action == 'skip_turn':
            return self._skip_turn_effect(effect, target_player)
        elif action == 'test_luck':
            return self._test_luck_effect(effect, player, target_player, target_organ)
        else:
            logger.warning(f"Unknown effect action: {action}")
            return {'success': False, 'error': f'Unknown action: {action}'}

    def _remove_organ_effect(self, effect: CardEffect, player, target_player: Player, target_organ):
        """Process organ removal effect."""
        if not target_player or not target_organ:
            return {'success': False, 'error': 'Missing target for organ removal'}

        # Check if organ is protected
        if target_player.is_organ_protected(target_organ):
            return {'success': False, 'blocked': True, 'reason': 'Organ is protected'}

        success = target_player.remove_organ(target_organ)
        return {
            'success': success,
            'action': 'remove_organ',
            'target': target_organ,
            'player': target_player.name
        }

    def _protect_organ_effect(self, effect: CardEffect, player, target_player, target_organ, card):
        """Process organ protection effect."""
        target = target_player or player
        organ_type = target_organ or effect.target_organ

        if not organ_type:
            return {'success': False, 'error': 'No target organ specified'}

        # Set protection_source to 'Vaccination' if the card is Vaccination
        protection_source = 'Vaccination' if getattr(effect, 'action', '').lower() == 'protect_organ' and getattr(
            card, 'name', '').lower() == 'vaccination' else f"Protected by {player.name}"
        success = target.protect_organ(organ_type, protection_source)
        return {
            'success': success,
            'action': 'protect_organ',
            'target': organ_type,
            'player': target.name
        }

    def _block_attack_effect(self, effect: CardEffect, player):
        """Process attack blocking effect."""
        # This would interact with the game engine's attack resolution
        return {
            'success': True,
            'action': 'block_attack',
            'player': player.name
        }

    def _steal_organ_effect(self, effect: CardEffect, player, target_player, target_organ):
        """Process organ stealing effect."""
        if not target_player or not target_organ:
            return {'success': False, 'error': 'Missing target for organ steal'}

        # Implementation would depend on game rules for organ stealing
        return {
            'success': False,
            'error': 'Organ stealing not fully implemented'
        }

    def _draw_cards_effect(self, effect: CardEffect, player):
        """Process card drawing effect."""
        draw_count = effect.value or 1

        for _ in range(draw_count):
            card = self.game_engine.draw_card_for_player(player)
            if not card:
                break

        return {
            'success': True,
            'action': 'draw_cards',
            'count': draw_count,
            'player': player.name
        }

    def _skip_turn_effect(self, effect: CardEffect, target_player):
        """Process turn skipping effect."""
        if target_player:
            target_player.skip_next_turn = True
            return {
                'success': True,
                'action': 'skip_turn',
                'player': target_player.name
            }
        return {'success': False, 'error': 'No target player for skip turn'}

    def _test_luck_effect(self, effect: CardEffect, player, target_player, target_organ):
        """Simulate a coin flip: heads does nothing, tails destroys the organ."""
        coin = random.choice(['heads', 'tails'])
        logger.info(f"Test luck: {coin}")

        result = {'success': True, 'action': 'test_luck', 'coin': coin}
        if coin == 'tails' and target_player and target_organ:
            destroyed = target_player.remove_organ(target_organ)
            result['organ_destroyed'] = destroyed
            result['target_player'] = target_player.name
            result['target_organ'] = target_organ
        return result
