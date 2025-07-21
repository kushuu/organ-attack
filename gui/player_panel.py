"""
Player panel widget showing player status, organs, and hand.
"""

import tkinter as tk
from tkinter import ttk
from typing import List

from game.game_engine import GameEngine
from game.player import Player
from gui.card_widget import CardWidget
from gui.organ_widget import OrganWidget


class PlayerPanel(ttk.Frame):
    """Panel displaying a player's status, organs, and cards."""

    def __init__(self, parent, player: Player, engine: GameEngine, main_window, is_current: bool = False):
        super().__init__(parent)
        self.player = player
        self.engine = engine
        self.main_window = main_window
        self.is_current = is_current

        # Visual elements
        self.header_frame = None
        self.organs_frame = None
        self.hand_frame = None
        self.card_widgets: List[CardWidget] = []
        self.organ_widgets: List[OrganWidget] = []

        self._create_layout()
        self.update_display()

    def _create_layout(self):
        """Create the panel layout."""
        # Configure grid
        self.columnconfigure(0, weight=1)

        # Header with player name and stats
        self.header_frame = ttk.Frame(self)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        self.name_label = ttk.Label(self.header_frame, text=self.player.name,
                                    font=('Arial', 14, 'bold'))
        self.name_label.pack(side=tk.LEFT)

        self.stats_label = ttk.Label(self.header_frame, text="")
        self.stats_label.pack(side=tk.RIGHT)

        # Organs display
        organs_label = ttk.Label(self, text="Organs:",
                                 font=('Arial', 10, 'bold'))
        organs_label.grid(row=1, column=0, sticky="w", padx=5)

        self.organs_frame = ttk.Frame(self)
        self.organs_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        # Hand display (only for current player or if showing hand)
        if self.is_current:
            hand_label = ttk.Label(
                self, text="Hand:", font=('Arial', 10, 'bold'))
            hand_label.grid(row=3, column=0, sticky="w", padx=5, pady=(10, 0))

            self.hand_frame = ttk.Frame(self)
            self.hand_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=2)
        else:
            # Show card count for other players
            self.card_count_label = ttk.Label(self, text="")
            self.card_count_label.grid(
                row=3, column=0, sticky="w", padx=5, pady=2)

    def update_display(self):
        """Update all display elements."""
        self._update_header()
        self._update_organs()
        if self.is_current:
            self._update_hand()
        else:
            self._update_card_count()

    def _update_header(self):
        """Update player name and stats in header."""
        # Color code based on player status
        if self.player.is_eliminated():
            name_color = 'red'
            name_text = f"{self.player.name} (ELIMINATED)"
        elif self.player == self.engine.get_current_player():
            name_color = 'blue'
            name_text = f"{self.player.name} (ACTIVE)"
        else:
            name_color = 'black'
            name_text = self.player.name

        self.name_label.config(text=name_text, foreground=name_color)

        # Stats
        organs_count = len(self.player.get_available_organs())
        hand_count = len(self.player.hand)
        stats_text = f"Organs: {organs_count} | Cards: {hand_count}"
        self.stats_label.config(text=stats_text)

    def _update_organs(self):
        """Update organ display."""
        # Clear existing organ widgets
        for widget in self.organ_widgets:
            widget.destroy()
        self.organ_widgets.clear()

        # Create organ widgets
        row = 0
        col = 0
        max_cols = 3

        for organ_name, organ_card in self.player.organs.items():
            organ_widget = OrganWidget(self.organs_frame, organ_card, self.engine,
                                       self.main_window, self.player)
            organ_widget.grid(row=row, column=col, padx=2, pady=2, sticky="ew")

            self.organ_widgets.append(organ_widget)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Configure grid weights
        for i in range(max_cols):
            self.organs_frame.columnconfigure(i, weight=1)

    def _update_hand(self):
        """Update hand display for current player."""
        if not self.hand_frame:
            return

        # Clear existing card widgets
        for widget in self.card_widgets:
            widget.destroy()
        self.card_widgets.clear()

        # Create card widgets
        for i, card in enumerate(self.player.hand):
            card_widget = CardWidget(self.hand_frame, card, self.engine,
                                     self.main_window, show_details=True, clickable=True)
            card_widget.grid(row=0, column=i, padx=2, pady=2)
            self.card_widgets.append(card_widget)

        # Configure grid weights
        for i in range(len(self.player.hand)):
            self.hand_frame.columnconfigure(i, weight=1)

    def _update_card_count(self):
        """Update card count for other players."""
        if hasattr(self, 'card_count_label'):
            count = len(self.player.hand)
            self.card_count_label.config(text=f"Cards in hand: {count}")
