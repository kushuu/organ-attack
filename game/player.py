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
    _skip_init: bool = field(default=False, repr=False)

    def __post_init__(self):
        """Initialize player with starting organs."""
        if not self._skip_init and not self.organs:
            self._initialize_organs()

    def _initialize_organs(self):
        """Initialize player with 6 random organs, loading HP from cards.json."""
        import json
        from pathlib import Path

        # Load organ definitions from JSON to get hit_points
        organ_defs = {}
        try:
            cards_path = Path("data/cards.json")
            if cards_path.exists():
                with open(cards_path, 'r') as f:
                    cards_data = json.load(f)
                for card in cards_data.get('cards', []):
                    if card.get('type') == 'Organ':
                        organ_defs[card['organ_type']] = card
        except Exception:
            pass

        organs = random.sample(list(self.organs_list), 6)
        logger.info(f"{self.name} has the following organs: {organs}")

        for organ_type in organs:
            organ_data = organ_defs.get(organ_type.value, {})
            hp = organ_data.get('hit_points', 1)
            organ_card = OrganCard(
                id=f"organ_{organ_type.value.lower()}",
                name=organ_type.value,
                type=CardType.ORGAN,
                description=organ_data.get('description', f"Essential {organ_type.value.lower()} organ."),
                organ_type=organ_type.value,
                is_vital=organ_type in self.vital_organs_list,
                can_be_protected=True,
                hit_points=hp,
                max_hit_points=hp
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
        """Remove (destroy) an organ instantly, bypassing HP."""
        if self.has_organ(organ_type):
            self.organs[organ_type].is_removed = True
            logger.info(f"{self.name}'s {organ_type} was removed!")
            self._check_elimination()
            return True
        return False

    def damage_organ(self, organ_type: str) -> bool:
        """Deal 1 damage to an organ. Returns True if organ was destroyed."""
        if not self.has_organ(organ_type):
            return False

        organ = self.organs[organ_type]
        organ.hit_points -= 1
        logger.info(f"{self.name}'s {organ_type} took 1 damage ({organ.hit_points}/{organ.max_hit_points})")

        if organ.hit_points <= 0:
            organ.is_removed = True
            logger.info(f"{self.name}'s {organ_type} was destroyed!")
            self._check_elimination()
            return True
        return False

    def protect_organ(self, organ_type: str, protection_source: str = "Unknown", expires_at: Optional[int] = None) -> bool:
        """Protect an organ from attacks."""
        if self.has_organ(organ_type):
            organ = self.organs[organ_type]
            if organ.can_be_protected:
                organ.is_protected = True
                organ.protection_source = protection_source
                organ.protection_expires_at = expires_at
                logger.info(
                    f"{self.name}'s {organ_type} is now protected by {protection_source} (expires turn {expires_at})")
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

    def can_play_card(self, card: Card, allow_play: bool = True) -> bool:
        """Check if a card can be played. allow_play=False when checking discard-only."""
        if card not in self.hand:
            return False
        if allow_play and self.cards_played_this_turn >= 2:
            return False
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

    def to_dict(self) -> dict:
        """Convert player to dictionary for network transmission."""
        hand_data = []
        for card in self.hand:
            try:
                card_dict = {
                    "id": card.id,
                    "name": card.name,
                    "type": card.type.value if card.type else "Unknown",
                    "description": card.description or "",
                    "organ_type": card.organ_type,
                    "target": None,
                    "effects": []
                }
                if card.target:
                    card_dict["target"] = {
                        "organ_type": getattr(card.target, 'organ_type', None),
                        "scope": getattr(card.target, 'scope', 'Single'),
                        "player_scope": getattr(card.target, 'player_scope', 'Other'),
                        "organ_scope": getattr(card.target, 'organ_scope', 'Single'),
                        "flexible": getattr(card.target, 'flexible', False)
                    }
                if card.effects:
                    for e in card.effects:
                        try:
                            card_dict["effects"].append({
                                "action": e.action,
                                "target_organ": e.target_organ,
                                "duration": e.duration,
                                "value": e.value
                            })
                        except Exception:
                            pass
                hand_data.append(card_dict)
            except Exception as ex:
                logger.error(f"Error serializing card {getattr(card, 'id', '?')}: {ex}")
                hand_data.append({
                    "id": getattr(card, 'id', 'unknown'),
                    "name": getattr(card, 'name', 'Unknown'),
                    "type": "Unknown",
                    "description": "",
                    "organ_type": None,
                    "target": None,
                    "effects": []
                })

        organs_data = {}
        for organ_type, organ in self.organs.items():
            try:
                organs_data[organ_type] = {
                    "id": organ.id,
                    "name": organ.name,
                    "organ_type": organ.organ_type,
                    "is_removed": organ.is_removed,
                    "is_protected": organ.is_protected,
                    "protection_source": organ.protection_source,
                    "protection_expires_at": organ.protection_expires_at,
                    "is_vital": organ.is_vital,
                    "hit_points": organ.hit_points,
                    "max_hit_points": organ.max_hit_points
                }
            except Exception as ex:
                logger.error(f"Error serializing organ {organ_type}: {ex}")

        return {
            "name": self.name,
            "organs": organs_data,
            "hand": hand_data,
            "status": self.status.value,
            "cards_played_this_turn": self.cards_played_this_turn,
            "cards_drawn_this_turn": self.cards_drawn_this_turn,
            "can_draw_extra": self.can_draw_extra,
            "skip_next_turn": self.skip_next_turn
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Create player from dictionary without generating random organs."""
        from game.models import CardType, Card, OrganCard

        player = cls(name=data["name"], _skip_init=True)
        player.status = PlayerStatus(data.get("status", "active"))
        player.cards_played_this_turn = data.get("cards_played_this_turn", 0)
        player.cards_drawn_this_turn = data.get("cards_drawn_this_turn", 0)
        player.can_draw_extra = data.get("can_draw_extra", False)
        player.skip_next_turn = data.get("skip_next_turn", False)

        # Restore organs from dict
        player.organs = {}
        for organ_type, org_data in data.get("organs", {}).items():
            organ = OrganCard(
                id=org_data["id"],
                name=org_data["name"],
                type=CardType.ORGAN,
                description="",
                organ_type=org_data["organ_type"],
                is_vital=org_data.get("is_vital", False),
                can_be_protected=True,
                is_removed=org_data.get("is_removed", False),
                is_protected=org_data.get("is_protected", False),
                protection_source=org_data.get("protection_source"),
                protection_expires_at=org_data.get("protection_expires_at"),
                hit_points=org_data.get("hit_points", 1),
                max_hit_points=org_data.get("max_hit_points", 1)
            )
            player.organs[organ_type] = organ

        # Restore hand
        player.hand = []
        for card_data in data.get("hand", []):
            card = Card(
                id=card_data["id"],
                name=card_data["name"],
                type=CardType(card_data["type"]),
                description=card_data.get("description", "")
            )
            player.hand.append(card)

        return player
