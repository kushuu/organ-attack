"""
Card widget for displaying individual cards in the GUI.
"""

import tkinter as tk
from tkinter import ttk

from game.cards import Card
from game.game_engine import GameEngine
from game.models import CardType
from gui.target_selector import TargetSelector


class CardWidget(ttk.Frame):
    """Widget for displaying and interacting with cards."""

    def __init__(self, parent, card: Card, engine: GameEngine, main_window,
                 show_details: bool = True, clickable: bool = True):
        super().__init__(parent, style='Card.TFrame')
        self.card = card
        self.engine = engine
        self.main_window = main_window
        self.show_details = show_details
        self.clickable = clickable

        # Color scheme based on card type
        self.colors = {
            CardType.ATTACK: {'bg': '#e74c3c', 'fg': 'white'},
            CardType.DEFENSE: {'bg': '#2ecc71', 'fg': 'white'},
            CardType.ACTION: {'bg': '#3498db', 'fg': 'white'},
            CardType.WILDCARD: {'bg': '#9b59b6', 'fg': 'white'},
            CardType.ORGAN: {'bg': '#f39c12', 'fg': 'white'}
        }

        self._create_layout()
        self._setup_interactions()

    def _create_layout(self):
        """Create the card layout."""
        # Configure frame
        self.configure(padding=5, relief='raised', borderwidth=2)

        # Get card colors
        color_scheme = self.colors.get(
            self.card.type, {'bg': '#95a5a6', 'fg': 'white'})

        # Card type indicator
        type_frame = tk.Frame(self, bg=color_scheme['bg'], height=20)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        type_label = tk.Label(type_frame, text=self.card.type.value,
                              bg=color_scheme['bg'], fg=color_scheme['fg'],
                              font=('Arial', 8, 'bold'))
        type_label.pack()

        # Card name
        name_label = ttk.Label(self, text=self.card.name,
                               font=('Arial', 10, 'bold'),
                               wraplength=120)
        name_label.pack(pady=2)

        if self.show_details:
            # Card description
            desc_label = ttk.Label(self, text=self.card.description,
                                   font=('Arial', 8),
                                   wraplength=120)
            desc_label.pack(pady=2)

            # Target info
            if self.card.target:
                target_text = self._get_target_text()
                if target_text:
                    target_label = ttk.Label(self, text=target_text,
                                             font=('Arial', 7),
                                             foreground='blue',
                                             wraplength=120)
                    target_label.pack(pady=1)

        # Configure minimum size
        self.configure(width=130, height=150 if self.show_details else 100)

    def _get_target_text(self) -> str:
        """Get target description text."""
        if not self.card.target:
            return ""

        target = self.card.target
        parts = []

        if target.organ_type:
            if target.organ_type == "Any":
                parts.append("Target: Any organ")
            else:
                parts.append(f"Target: {target.organ_type}")

        if target.player_scope != "Other":
            parts.append(f"Players: {target.player_scope}")

        return " | ".join(parts)

    def _setup_interactions(self):
        """Setup mouse interactions."""
        if self.clickable:
            self.bind("<Button-1>", self._on_click)
            self.bind("<Enter>", self._on_hover_enter)
            self.bind("<Leave>", self._on_hover_leave)

            # Bind to all child widgets too
            for child in self.winfo_children():
                child.bind("<Button-1>", self._on_click)
                child.bind("<Enter>", self._on_hover_enter)
                child.bind("<Leave>", self._on_hover_leave)

        # Tooltip on hover (for all cards)
        # self.bind("<Enter>", self._show_tooltip)
        # self.bind("<Leave>", self._hide_tooltip)
        self.tooltip = None

    def _on_click(self, event):
        """Handle card click."""
        if not self.clickable:
            return

        # Check if it's current player's turn
        current_player = self.engine.get_current_player()
        if self.card not in current_player.hand:
            return

        # Handle different game states
        game_state = self.engine.game_state

        if game_state.name != 'PLAY':
            self.main_window._update_status(
                f"Cannot play cards during {game_state.name} phase")
            return

        # Get targets if needed
        target_player, target_organ = self._get_targets()

        if self.card.target and target_player is None and target_organ is None:
            return  # Target selection was cancelled

        # Play the card
        self.main_window.play_card(self.card, target_player, target_organ)

    def _get_targets(self):
        """Get targets for the card using target selector."""
        if not self.card.target:
            return None, None

        selector = TargetSelector(
            self.main_window, self.card, self.engine)
        return selector.get_targets()

    def _on_hover_enter(self, event):
        """Handle mouse enter for clickable cards."""
        if self.clickable:
            self.configure(relief='ridge')

    def _on_hover_leave(self, event):
        """Handle mouse leave for clickable cards."""
        if self.clickable:
            self.configure(relief='raised')

    def _show_tooltip(self, event):
        """Show detailed tooltip."""
        if self.tooltip:
            return

        # Create tooltip window
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)

        # Position tooltip
        x = self.winfo_rootx() + 20
        y = self.winfo_rooty() + 20
        self.tooltip.geometry(f"+{x}+{y}")

        # Tooltip content
        tooltip_text = f"{self.card.name}\n\n{self.card.description}"

        if self.card.effects:
            tooltip_text += "\n\nEffects:"
            for effect in self.card.effects:
                tooltip_text += f"\n• {effect.action.replace('_', ' ').title()}"

        label = tk.Label(self.tooltip, text=tooltip_text,
                         background='lightyellow', relief='solid',
                         borderwidth=1, font=('Arial', 9),
                         justify=tk.LEFT, wraplength=200)
        label.pack()

    def _hide_tooltip(self, event):
        """Hide tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
