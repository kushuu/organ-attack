"""
Player management for the Organ Attack card game.
Handles player state, organs, hand management, and actions.
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.models import Card, CardType, OrganCard, OrganType, PlayerStatus

logger = logging.getLogger(__name__)


@dataclass
class Player:
    """Represents a player in the Organ Attack game."""
    name: str
    organs: Dict[str, OrganCard] = field(default_factory=dict)
    hand: List[Card] = field(default_factory=list)
    status: PlayerStatus = PlayerStatus.ACTIVE
    cards_played_this_turn: int = 0
    cards_drawn_this_turn: int = 0
    can_draw_extra: bool = False
    skip_next_turn: bool = False
    organs_list: Tuple[OrganType] = tuple(
        organ for organ in OrganType
    )
    vital_organs_list: Tuple[OrganType] = (
        OrganType.HEART, OrganType.BRAIN, OrganType.LIVER,
        OrganType.KIDNEYS, OrganType.LUNGS, OrganType.STOMACH
    )

    def __post_init__(self):
        """Initialize player with starting organs."""
        if not self.organs:
            self._initialize_organs()

    def _initialize_organs(self):
        """Initialize player with the standard set of organ cards."""

        organs = random.sample(self.organs_list, 6)
        logger.info(f"{self.name} has the following organs: {organs}")
        # remove the selected organs from the list
        self.organs_list = [
            organ for organ in self.organs_list if organ not in organs]

        for organ_type in organs:
            organ_card = OrganCard(
                id=f"organ_{organ_type.value.lower()}",
                name=organ_type.value,
                type=CardType.ORGAN,
                description=f"Essential {organ_type.value.lower()} organ.",
                organ_type=organ_type.value,
                is_vital=organ_type in self.vital_organs_list,
                can_be_protected=True
            )
            self.organs[organ_type.value] = organ_card

    def add_card_to_hand(self, card: Card):
        """Add a card to the player's hand."""
        self.hand.append(card)
        logger.info(f"{self.name} drew {card.name}")

    def remove_card_from_hand(self, card: Card) -> bool:
        """Remove a card from the player's hand."""
        if card in self.hand:
            self.hand.remove(card)
            logger.info(f"{self.name} played {card.name}")
            return True
        return False

    def has_organ(self, organ_type: str) -> bool:
        """Check if player has a specific organ that's not removed."""
        return (organ_type in self.organs and
                not self.organs[organ_type].is_removed)

    def get_organ(self, organ_type: str) -> Optional[OrganCard]:
        """Get a specific organ card if it exists and is not removed."""
        if self.has_organ(organ_type):
            return self.organs[organ_type]
        return None

    def remove_organ(self, organ_type: str) -> bool:
        """Remove (destroy) an organ."""
        if self.has_organ(organ_type):
            self.organs[organ_type].is_removed = True
            logger.info(f"{self.name}'s {organ_type} was removed!")
            self._check_elimination()
            return True
        return False

    def protect_organ(self, organ_type: str, protection_source: str = "Unknown") -> bool:
        """Protect an organ from attacks."""
        if self.has_organ(organ_type):
            organ = self.organs[organ_type]
            if organ.can_be_protected:
                organ.is_protected = True
                organ.protection_source = protection_source
                logger.info(
                    f"{self.name}'s {organ_type} is now protected by {protection_source}")
                return True
        return False

    def unprotect_organ(self, organ_type: str) -> bool:
        """Remove protection from an organ."""
        if self.has_organ(organ_type):
            organ = self.organs[organ_type]
            if organ.is_protected:
                organ.is_protected = False
                organ.protection_source = None
                logger.info(
                    f"{self.name}'s {organ_type} protection was removed")
                return True
        return False

    def is_organ_protected(self, organ_type: str) -> bool:
        """Check if an organ is protected."""
        if self.has_organ(organ_type):
            return self.organs[organ_type].is_protected
        return False

    def get_available_organs(self) -> List[OrganCard]:
        """Get all organs that are still present (not removed)."""
        return [organ for organ in self.organs.values() if not organ.is_removed]

    def get_protected_organs(self) -> List[OrganCard]:
        """Get all organs that are protected."""
        return [organ for organ in self.organs.values()
                if not organ.is_removed and organ.is_protected]

    def _check_elimination(self):
        """Check if player should be eliminated (no organs left)."""
        available_organs = self.get_available_organs()
        if not available_organs:
            self.status = PlayerStatus.ELIMINATED
            logger.info(f"{self.name} has been eliminated!")

    def is_eliminated(self) -> bool:
        """Check if player is eliminated."""
        return self.status == PlayerStatus.ELIMINATED

    def get_hand_size(self) -> int:
        """Get the current hand size."""
        return len(self.hand)

    def needs_to_discard(self, hand_limit: int = 5) -> bool:
        """Check if player needs to discard cards."""
        return len(self.hand) > hand_limit

    def can_play_card(self, card: Card) -> bool:
        """Check if a card can be played based on game rules."""
        if card not in self.hand:
            return False

        # Basic validation - more complex validation happens in game engine
        if card.type == CardType.DEFENSE:
            # Defense cards are usually played in response to attacks
            return True

        return True

    def get_playable_cards(self) -> List[Card]:
        """Get all cards that can currently be played."""
        return [card for card in self.hand if self.can_play_card(card)]

    def get_cards_by_type(self, card_type: CardType) -> List[Card]:
        """Get all cards of a specific type from hand."""
        return [card for card in self.hand if card.type == card_type]

    def reset_turn_counters(self):
        """Reset per-turn counters."""
        self.cards_drawn_this_turn = 0
        self.cards_played_this_turn = 0
        self.can_draw_extra = False

    def get_status_summary(self) -> Dict[str, any]:
        """Get a summary of player status for display."""
        available_organs = self.get_available_organs()
        protected_organs = self.get_protected_organs()

        return {
            'name': self.name,
            'status': self.status.value,
            'hand_size': len(self.hand),
            'organs_remaining': len(available_organs),
            'organs_protected': len(protected_organs),
            'organ_details': {
                organ.organ_type: {
                    'present': not organ.is_removed,
                    'protected': organ.is_protected,
                    'protection_source': organ.protection_source
                } for organ in self.organs.values()
            }
        }

    def __str__(self) -> str:
        """String representation of the player."""
        available_organs = len(self.get_available_organs())
        return f"{self.name} ({available_organs} organs, {len(self.hand)} cards)"
