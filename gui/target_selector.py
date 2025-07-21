"""
Target selection dialog for cards that require targets.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Tuple

from game.cards import Card
from game.game_engine import GameEngine
from game.player import Player


class TargetSelector:
    """Dialog for selecting targets for cards."""

    def __init__(self, parent, card: Card, engine: GameEngine):
        self.parent = parent
        self.card = card
        self.engine = engine
        self.result_player: Optional[Player] = None
        self.result_organ: Optional[str] = None

        self.dialog = None
        self.player_var = None
        self.organ_var = None

    def get_targets(self) -> Tuple[Optional[Player], Optional[str]]:
        """Show target selection dialog and return selected targets."""
        if not self.card.target:
            return None, None

        self._create_dialog()
        return self.result_player, self.result_organ

    def _create_dialog(self):
        """Create the target selection dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Select Target for {self.card.name}")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"400x300+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text=f"Select target for: {self.card.name}",
                                font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        # Description
        desc_label = ttk.Label(main_frame, text=self.card.description,
                               wraplength=350, justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))

        # Target selection
        self._create_target_selection(main_frame)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=(20, 0))

        ok_button = ttk.Button(button_frame, text="OK",
                               command=self._ok_clicked)
        ok_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self._cancel_clicked)
        cancel_button.pack(side=tk.LEFT)

        # Make dialog modal
        self.dialog.wait_window()

    def _create_target_selection(self, parent):
        """Create target selection widgets."""
        target = self.card.target
        current_player = self.engine.get_current_player()

        # Player selection
        if target.player_scope in ["Other", "Any"]:
            player_frame = ttk.LabelFrame(parent, text="Select Player")
            player_frame.pack(fill=tk.X, pady=(0, 10))

            if target.player_scope == "Other":
                players = self.engine.get_other_players(current_player)
            else:  # Any
                players = self.engine.get_active_players()

            self.player_var = tk.StringVar()

            for i, player in enumerate(players):
                organs_count = len(player.get_available_organs())
                text = f"{player.name} ({organs_count} organs)"

                rb = ttk.Radiobutton(player_frame, text=text,
                                     variable=self.player_var, value=player.name,
                                     command=self._player_selected)
                rb.pack(anchor=tk.W, padx=10, pady=2)

                if i == 0:  # Select first player by default
                    self.player_var.set(player.name)
                    self.result_player = player

        elif target.player_scope == "Self":
            self.result_player = current_player

        # Organ selection
        if target.organ_type:
            organ_frame = ttk.LabelFrame(parent, text="Select Organ")
            organ_frame.pack(fill=tk.X, pady=(0, 10))

            if target.organ_type == "Any":
                self._create_organ_selection(organ_frame)
            else:
                # Specific organ type
                self.result_organ = target.organ_type
                organ_label = ttk.Label(
                    organ_frame, text=f"Target: {target.organ_type}")
                organ_label.pack(padx=10, pady=5)

        # Auto-select if only one option
        if target.player_scope == "Self" and target.organ_type != "Any":
            self.result_player = current_player

    def _create_organ_selection(self, parent):
        """Create organ selection widgets."""
        target_player = self.result_player or self.engine.get_current_player()
        available_organs = target_player.get_available_organs()

        if not available_organs:
            no_organs_label = ttk.Label(
                parent, text="No available organs to target")
            no_organs_label.pack(padx=10, pady=5)
            return

        self.organ_var = tk.StringVar()

        for i, organ in enumerate(available_organs):
            status_text = ""
            if organ.is_protected:
                status_text = " (Protected)"
            elif organ.is_vital:
                status_text = " (Vital)"

            text = f"{organ.organ_type}{status_text}"

            rb = ttk.Radiobutton(parent, text=text,
                                 variable=self.organ_var, value=organ.organ_type)
            rb.pack(anchor=tk.W, padx=10, pady=2)

            if i == 0:  # Select first organ by default
                self.organ_var.set(organ.organ_type)
                self.result_organ = organ.organ_type

    def _player_selected(self):
        """Handle player selection change."""
        if not self.player_var:
            return

        player_name = self.player_var.get()
        self.result_player = next(
            (p for p in self.engine.players if p.name == player_name), None)

        # Update organ selection if needed
        if self.card.target.organ_type == "Any":
            # Recreate organ selection for new player
            for widget in self.dialog.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.LabelFrame) and child.cget('text') == "Select Organ":
                            for organ_widget in child.winfo_children():
                                organ_widget.destroy()
                            self._create_organ_selection(child)
                            break

    def _ok_clicked(self):
        """Handle OK button click."""
        # Validate selections
        if self.card.target.player_scope in ["Other", "Any"] and not self.result_player:
            messagebox.showerror("Error", "Please select a target player")
            return

        if self.card.target.organ_type == "Any" and not self.result_organ:
            messagebox.showerror("Error", "Please select a target organ")
            return

        # Get final selections
        if self.organ_var:
            self.result_organ = self.organ_var.get()

        self.dialog.destroy()

    def _cancel_clicked(self):
        """Handle Cancel button click."""
        self.result_player = None
        self.result_organ = None
        self.dialog.destroy()
