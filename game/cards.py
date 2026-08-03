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

                card_type = CardType(card.type.value)
                self.cards_by_type[card_type].append(card)

            except Exception as e:
                logger.error(
                    f"Error parsing card {card_data.get('id', 'unknown')}: {e}")

    def _create_card_from_data(self, data: Dict[str, Any]) -> Card:
        """Create a Card object from JSON data."""
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

        card_type = CardType(data['type'])

        if card_type == CardType.ORGAN:
            hp = data.get('hit_points', 1)
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
                can_be_protected=data.get('can_be_protected', True),
                hit_points=hp,
                max_hit_points=hp
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

        basic_defenses = [
            {
                'id': 'defense_001',
                'name': 'Medical Kit',
                'type': 'Defense',
                'description': 'Block any attack.',
                'effects': [{'action': 'block_attack'}]
            }
        ]

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

    def validate_card_play(self, card: Card, player: Player, game_engine=None) -> tuple[bool, str]:
        """Validate if a card can be played based on its conditions."""
        if not card:
            return False, "Invalid card"

        if card not in player.hand:
            return False, "Card not in hand"

        if not card.conditions:
            return True, "Valid"

        conditions = card.conditions

        # Check: organ_must_be_present — player must have at least one non-removed organ
        if conditions.organ_must_be_present:
            available = player.get_available_organs()
            if not available:
                return False, "No organs present to use this card"

        # Check: organ_must_not_be_protected — player must have an unprotected organ
        if conditions.organ_must_not_be_protected:
            unprotected = [o for o in player.get_available_organs() if not o.is_protected]
            if not unprotected:
                return False, "All organs are protected"

        # Check: player_must_have_available_slot — player must have fewer than 6 organs
        if conditions.player_must_have_available_slot:
            available = player.get_available_organs()
            if len(available) >= 6:
                return False, "All organ slots are full"

        # Check: target_organ_must_be_present — target must have the specified organ
        if conditions.target_organ_must_be_present and game_engine:
            # This is validated against the target player at play time, not here
            pass

        # Check: must_be_played_in_response_or_attack_phase — wildcard/defense cards
        # Allow during active gameplay (PLAY state) — no separate attack phase in this game
        if conditions.must_be_played_in_response_or_attack_phase:
            if game_engine and game_engine.game_state.value != 1:  # GameState.PLAY
                return False, "Can only be played during active gameplay"

        return True, "Valid"


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
                if isinstance(result, list):
                    results.extend(result)
                else:
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
            return self._draw_cards_effect(effect, player, card)
        elif action == 'skip_turn':
            return self._skip_turn_effect(effect, target_player)
        elif action == 'test_luck':
            return self._test_luck_effect(effect, player, target_player, target_organ)
        elif action == 'extra_turn':
            return self._extra_turn_effect(effect, player)
        elif action == 'mass_discard':
            return self._mass_discard_effect(effect, player)
        elif action == 'mimic_card':
            return self._mimic_card_effect(effect, card, player, target_player, target_organ)
        else:
            logger.warning(f"Unknown effect action: {action}")
            return {'success': False, 'error': f'Unknown action: {action}'}

    def _remove_organ_effect(self, effect: CardEffect, player, target_player: Player, target_organ):
        """Process organ damage effect. Reduces organ HP by 1."""
        if not target_player or not target_organ:
            return {'success': False, 'error': 'Missing target for organ removal'}

        # Check if organ is protected
        if target_player.is_organ_protected(target_organ):
            return {'success': False, 'blocked': True, 'reason': 'Organ is protected'}

        destroyed = target_player.damage_organ(target_organ)
        return {
            'success': True,
            'action': 'remove_organ',
            'target': target_organ,
            'player': target_player.name,
            'destroyed': destroyed
        }

    def _protect_organ_effect(self, effect: CardEffect, player, target_player, target_organ, card):
        """Process organ protection effect."""
        target = target_player or player
        organ_type = target_organ or effect.target_organ

        if not organ_type:
            return {'success': False, 'error': 'No target organ specified'}

        protection_source = 'Vaccination' if card.name.lower() == 'vaccination' else f"Protected by {player.name}"

        # Vaccination protection expires after 2 full rounds (num_players * 2 turns)
        expires_at = None
        if card.name.lower() == 'vaccination':
            num_players = len(self.game_engine.players)
            expires_at = self.game_engine.turn_count + (num_players * 2)

        success = target.protect_organ(organ_type, protection_source, expires_at)
        return {
            'success': success,
            'action': 'protect_organ',
            'target': organ_type,
            'player': target.name,
            'expires_at': expires_at
        }

    def _block_attack_effect(self, effect: CardEffect, player):
        """Process attack blocking effect. Sets the pending defense flag."""
        # Mark that this player has played a defense card
        if self.game_engine.current_attack:
            self.game_engine.current_attack['blocked'] = True
            self.game_engine.current_attack['blocked_by'] = player.name
        self.game_engine.pending_defense = False

        return {
            'success': True,
            'action': 'block_attack',
            'player': player.name
        }

    def _steal_organ_effect(self, effect: CardEffect, player, target_player, target_organ):
        """Process organ stealing effect. Removes organ from target, adds to player."""
        if not target_player or not target_organ:
            return {'success': False, 'error': 'Missing target for organ steal'}

        # Check if target has the organ
        if not target_player.has_organ(target_organ):
            return {'success': False, 'error': f'{target_player.name} does not have {target_organ}'}

        # Check if organ is protected
        if target_player.is_organ_protected(target_organ):
            return {'success': False, 'blocked': True, 'reason': 'Organ is protected'}

        # Check if player already has this organ
        if player.has_organ(target_organ):
            return {'success': False, 'error': f'You already have a {target_organ}'}

        # Remove from target
        target_organ_card = target_player.organs[target_organ]
        target_player.remove_organ(target_organ)
        # Delete the entry from target's dict so the shared reference is gone
        del target_player.organs[target_organ]

        # Add to player (reset flags for new owner)
        target_organ_card.is_removed = False
        target_organ_card.is_protected = False
        target_organ_card.protection_source = None
        player.organs[target_organ] = target_organ_card

        return {
            'success': True,
            'action': 'steal_organ',
            'target': target_organ,
            'from_player': target_player.name,
            'to_player': player.name
        }

    def _draw_cards_effect(self, effect: CardEffect, player, card=None):
        """Process card drawing effect. If card target scope is 'All', all players draw."""
        draw_count = effect.value or 1
        results = []

        scope = card.target.player_scope if card and card.target else 'Self'

        if scope == 'All':
            for p in self.game_engine.players:
                if p.status == 'eliminated':
                    continue
                actual_count = 0
                for _ in range(draw_count):
                    drawn = self.game_engine.draw_card_for_player(p)
                    if not drawn:
                        break
                    actual_count += 1
                results.append({
                    'success': True,
                    'action': 'draw_cards',
                    'count': actual_count,
                    'player': p.name
                })
        else:
            actual_count = 0
            for _ in range(draw_count):
                card_drawn = self.game_engine.draw_card_for_player(player)
                if not card_drawn:
                    break
                actual_count += 1
            results.append({
                'success': True,
                'action': 'draw_cards',
                'count': actual_count,
                'player': player.name
            })

        return results

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
            # Check protection before destroying
            if target_player.is_organ_protected(target_organ):
                result['organ_destroyed'] = False
                result['reason'] = 'Organ is protected'
            else:
                destroyed = target_player.damage_organ(target_organ)
                result['organ_destroyed'] = destroyed
                result['target_player'] = target_player.name
                result['target_organ'] = target_organ
        return result

    def _extra_turn_effect(self, effect: CardEffect, player):
        """Grant the player an extra turn after the current turn ends."""
        # Mark the player to get an extra turn
        player.can_draw_extra = True
        return {
            'success': True,
            'action': 'extra_turn',
            'player': player.name
        }

    def _mass_discard_effect(self, effect: CardEffect, player):
        """All other players discard half their hand (rounded down)."""
        import math
        discarded = []
        for other_player in self.game_engine.get_other_players(player):
            discard_count = math.floor(len(other_player.hand) / 2)
            for _ in range(discard_count):
                if not other_player.hand:
                    break
                random_card = random.choice(other_player.hand)
                other_player.remove_card_from_hand(random_card)
                self.game_engine.discard_pile.append(random_card)
                discarded.append({
                    'player': other_player.name,
                    'card': random_card.name
                })

        return {
            'success': True,
            'action': 'mass_discard',
            'discarded': discarded,
            'player': player.name
        }

    def _mimic_card_effect(self, effect: CardEffect, card: Card, player, target_player, target_organ):
        """Mimic another card's effect. Uses the mimic_type from the card effect."""
        if not effect.mimic_type:
            return {'success': False, 'error': 'No mimic type specified'}

        # Handle pipe-separated types (e.g., "Attack|Defense") — pick based on context
        mimic_type = effect.mimic_type
        if '|' in mimic_type:
            options = [t.strip() for t in mimic_type.split('|')]
            if self.game_engine.pending_defense and 'Defense' in options:
                mimic_type = 'Defense'
            elif 'Attack' in options:
                mimic_type = 'Attack'
            else:
                mimic_type = options[0]

        # Find a card of the specified type in the discard pile or create a virtual one
        mimic_card = None
        for discarded_card in self.game_engine.discard_pile:
            if discarded_card.type.value.lower() == mimic_type.lower():
                mimic_card = discarded_card
                break

        if not mimic_card:
            # Create a basic virtual card of the requested type
            if mimic_type.lower() == 'attack':
                return self._remove_organ_effect(
                    CardEffect(action='remove_organ', target_organ=target_organ),
                    player, target_player, target_organ
                )
            elif mimic_type.lower() == 'defense':
                return self._block_attack_effect(effect, player)
            elif mimic_type.lower() == 'action':
                return self._draw_cards_effect(
                    CardEffect(action='draw_cards', value=1), player
                )
            else:
                return {'success': False, 'error': f'Cannot mimic {mimic_type}'}

        # Process the mimicked card's effects
        results = self.process_card_effects(mimic_card, player, target_player, target_organ)
        return {
            'success': True,
            'action': 'mimic_card',
            'mimicked': mimic_card.name,
            'effects': results,
            'player': player.name
        }
