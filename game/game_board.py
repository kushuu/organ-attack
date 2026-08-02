import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from game.game_engine import GameEngine
from game.models import GameState
from gui.player_panel import PlayerPanel


class GameBoard(ttk.Frame):
    """Main game board displaying all players and game state."""

    def __init__(self, parent, engine: GameEngine, main_window):
        super().__init__(parent)
        self.engine = engine
        self.main_window = main_window

        self.player_panels: List[PlayerPanel] = []
        self.current_player_panel: Optional[PlayerPanel] = None

        self.control_frame = None
        self.phase_label = None
        self.action_buttons = {}

        self._rebuilding = False

        self._create_layout()
        self._create_controls()

    def _create_layout(self):
        """Create the main layout structure."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=3)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        self.players_frame = ttk.Frame(self)
        self.players_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.current_player_frame = ttk.LabelFrame(self, text="Your Hand")
        self.current_player_frame.grid(
            row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.control_frame = ttk.Frame(self)
        self.control_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        self._create_player_panels()

    def _create_controls(self):
        """Create game control buttons."""
        self.phase_label = ttk.Label(self.control_frame, text="",
                                     font=('Arial', 12, 'bold'))
        self.phase_label.pack(side=tk.LEFT, padx=10)

        button_frame = ttk.Frame(self.control_frame)
        button_frame.pack(side=tk.RIGHT, padx=10)

        self.action_buttons = {
            'draw': ttk.Button(button_frame, text="Draw Card",
                               command=self._draw_card),
            'end_turn': ttk.Button(button_frame, text="End Turn",
                                   command=self._end_turn),
            'show_deck': ttk.Button(button_frame, text="Deck Info",
                                    command=self._show_deck_info)
        }

        for button in self.action_buttons.values():
            button.pack(side=tk.LEFT, padx=5)

    def _draw_card(self):
        """Handle draw card button."""
        self.main_window.draw_card()

    def _end_turn(self):
        """Handle end turn button."""
        self.main_window.advance_turn()

    def _create_player_panels(self):
        """Create panels for all players."""
        players = self.engine.players
        current_player = self.engine.get_current_player()

        other_players = [p for p in players if p != current_player]

        cols = min(len(other_players), 3)
        rows = (len(other_players) + cols - 1) // cols if cols > 0 else 0

        for i in range(cols):
            self.players_frame.columnconfigure(i, weight=1)
        for i in range(rows):
            self.players_frame.rowconfigure(i, weight=1)

        for i, player in enumerate(other_players):
            row = i // cols
            col = i % cols

            panel = PlayerPanel(self.players_frame, player, self.engine, self.main_window,
                                is_current=False)
            panel.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            self.player_panels.append(panel)

        self.current_player_panel = PlayerPanel(self.current_player_frame, current_player,
                                                self.engine, self.main_window, is_current=True)
        self.current_player_panel.pack(
            fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _update_button_states(self):
        """Update button states based on game phase."""
        game_state = self.engine.game_state

        for button in self.action_buttons.values():
            button.config(state='disabled')

        if game_state == GameState.PLAY:
            self.action_buttons['draw'].config(state='normal')
            self.action_buttons['end_turn'].config(state='normal')

        self.action_buttons['show_deck'].config(state='normal')

    def update_display(self):
        """Update the entire game board display."""
        if not self.engine:
            return

        game_state = self.engine.game_state
        current_player = self.engine.get_current_player()

        if game_state == GameState.PLAY:
            phase_text = f"Phase: PLAY | Player: {current_player.name}"
        elif game_state == GameState.DONE:
            phase_text = f"Phase: DONE | Move on to the next person!"
        else:
            phase_text = f"Phase: {game_state.name} | Player: {current_player.name}"
        self.phase_label.config(text=phase_text)

        self._update_button_states()

        for panel in self.player_panels:
            panel.update_display()

        if self.current_player_panel:
            self.current_player_panel.update_display()

        # Check if current player changed — rebuild panels if needed
        if (self.current_player_panel and
                self.current_player_panel.player != current_player and
                not self._rebuilding):
            self._rebuild_player_panels()

    def _show_deck_info(self):
        """Show deck information dialog."""
        deck_size = len(self.engine.deck)
        discard_size = len(self.engine.discard_pile)

        info_text = f"Deck: {deck_size} cards\nDiscard pile: {discard_size} cards"

        info_window = tk.Toplevel(self.main_window)
        info_window.title("Deck Information")
        info_window.geometry("300x150")
        info_window.resizable(False, False)
        info_window.transient(self.main_window)
        info_window.grab_set()

        ttk.Label(info_window, text=info_text,
                  font=('Arial', 12)).pack(pady=20)
        ttk.Button(info_window, text="Close",
                   command=info_window.destroy).pack(pady=10)

    def _rebuild_player_panels(self):
        """Rebuild player panels when current player changes."""
        if self._rebuilding:
            return
        self._rebuilding = True

        try:
            for panel in self.player_panels:
                panel.destroy()
            self.player_panels.clear()

            if self.current_player_panel:
                self.current_player_panel.destroy()

            for widget in self.players_frame.winfo_children():
                widget.destroy()
            for widget in self.current_player_frame.winfo_children():
                widget.destroy()

            self._create_player_panels()
        finally:
            self._rebuilding = False
