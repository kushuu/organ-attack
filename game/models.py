"""
Core data models for the Organ Attack card game.
Defines the fundamental data structures using dataclasses and enums.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class CardType(Enum):
    """Enumeration of all card types in the game."""
    ORGAN = "Organ"
    ATTACK = "Attack"
    DEFENSE = "Defense"
    ACTION = "Action"
    WILDCARD = "Wildcard"


class GameState(Enum):
    """Game state machine states."""
    PLAY = auto()
    DONE = auto()


class PlayerStatus(Enum):
    """Player status enumeration."""
    ACTIVE = "active"
    ELIMINATED = "eliminated"


class OrganType(Enum):
    """Types of organs in the game."""
    HEART = "Heart"
    BRAIN = "Brain"
    LUNGS = "Lungs"
    KIDNEYS = "Kidneys"
    EYES = "Eyes"
    LIVER = "Liver"
    STOMACH = "Stomach"
    INTESTINES = "Intestines"
    BLADDER = "Bladder"
    BOWELS = "Bowels"
    PANCREAS = "Pancreas"
    SPLEEN = "Spleen"
    APPENDIX = "Appendix"
    TONGUE = "Tongue"
    TONSILS = "Tonsils"
    THYROID = "Thyroid"
    TEETH = "Teeth"
    GALLBLADDER = "Gallbladder"
    ESOPHAGUS = "Esophagus"


@dataclass
class CardTarget:
    """Defines targeting information for a card."""
    organ_type: Optional[str] = None
    scope: str = "Single"  # Single, Multiple, All
    player_scope: str = "Other"  # Self, Other, Any, All
    organ_scope: str = "Single"  # Single, Multiple, All
    flexible: bool = False


@dataclass
class CardConditions:
    """Defines conditions that must be met for a card to be played."""
    organ_must_be_present: bool = False
    organ_must_not_be_protected: bool = False
    target_organ_must_be_present: bool = False
    player_must_have_available_slot: bool = False
    must_be_played_in_response_or_attack_phase: bool = False


@dataclass
class CardEffect:
    """Defines an effect that a card can have when played."""
    action: str
    target_organ: Optional[str] = None
    duration: str = "instant"  # instant, permanent, turns
    value: Optional[int] = None
    mimic_type: Optional[str] = None
    from_target: Optional[str] = None
    to_target: Optional[str] = None


@dataclass
class Card:
    """Base card class with all common attributes."""
    id: str
    name: str
    type: CardType
    description: str
    target: Optional[CardTarget] = None
    conditions: Optional[CardConditions] = None
    effects: List[CardEffect] = field(default_factory=list)
    organ_type: Optional[str] = None
    is_vital: bool = False
    can_be_protected: bool = True


@dataclass
class OrganCard(Card):
    """Represents an organ card with protection status."""
    is_removed: bool = False
    is_protected: bool = False
    protection_source: Optional[str] = None

    def __post_init__(self):
        """Set card type to Organ after initialization."""
        self.type = CardType.ORGAN


@dataclass
class GameEvent:
    """Represents a game event for logging and state management."""
    event_type: str
    player_name: str
    card_played: Optional[str] = None
    target_player: Optional[str] = None
    target_organ: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActiveEffect:
    """Represents an active effect on the game state."""
    effect_id: str
    source_card: str
    target_player: Optional[str]
    target_organ: Optional[str]
    duration: str  # instant, permanent, turns
    turns_remaining: int = 0
    effect_data: Dict[str, Any] = field(default_factory=dict)


class TurnDirection(Enum):
    CLOCKWISE = 1
    ANTICLOCKWISE = -1
