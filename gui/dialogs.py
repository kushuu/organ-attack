import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

import logging

logger = logging.getLogger(__name__)


class NewGameDialog:
    """Dialog for setting up a new game."""

    def __init__(self, parent):
        self.parent = parent
        self.result: Optional[List[str]] = None
        self.player_entries: List[tk.Entry] = []
        self.width = 400
        self.height = 350
        self.dimensions = f"{self.width}x{self.height}"

        self._create_dialog()

    def _create_dialog(self):
        """Create the new game dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("New Game Setup")
        self.dialog.geometry(f"{self.dimensions}")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.height // 2)
        self.dialog.geometry(f"{self.dimensions}+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text="New Game Setup",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(main_frame,
                                 text="Enter player names (2-4 players):",
                                 font=('Arial', 11))
        instructions.pack(pady=(0, 10))

        # Player name entries
        self.entries_frame = ttk.Frame(main_frame)
        self.entries_frame.pack(fill=tk.X, pady=(0, 20))

        # Create initial entries for 2 players
        for i in range(2):
            self._add_player_entry(f"Player {i + 1}")

        # Add/Remove buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))

        add_button = ttk.Button(button_frame, text="Add Player",
                                command=self._add_player)
        add_button.pack(side=tk.LEFT)

        remove_button = ttk.Button(button_frame, text="Remove Player",
                                   command=self._remove_player)
        remove_button.pack(side=tk.LEFT, padx=(10, 0))

        # OK/Cancel buttons
        ok_cancel_frame = ttk.Frame(main_frame)
        ok_cancel_frame.pack(side=tk.BOTTOM)

        ok_button = ttk.Button(ok_cancel_frame, text="Start Game",
                               command=self._ok_clicked)
        ok_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(ok_cancel_frame, text="Cancel",
                                   command=self._cancel_clicked)
        cancel_button.pack(side=tk.LEFT)

        # Focus first entry
        if self.player_entries:
            self.player_entries[0].focus()

        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._ok_clicked())

        self.dialog.wait_window()

    def _add_player_entry(self, placeholder: str = ""):
        """Add a new player entry field."""
        entry = ttk.Entry(self.entries_frame, font=('Arial', 11))
        entry.pack(fill=tk.X, pady=2)
        if placeholder:
            entry.insert(0, placeholder)

        self.player_entries.append(entry)

    def _add_player(self):
        """Add another player entry."""
        if len(self.player_entries) < 4:
            self._add_player_entry(f"Player {len(self.player_entries) + 1}")

    def _remove_player(self):
        """Remove the last player entry."""
        if len(self.player_entries) > 2:
            entry = self.player_entries.pop()
            entry.destroy()
        else:
            messagebox.showwarning("Warning", "At least 2 players required!")

    def _ok_clicked(self):
        """Handle OK button click."""
        # Get player names
        names = []
        for entry in self.player_entries:
            name = entry.get().strip()
            if name:
                names.append(name)

        # Validate
        if len(names) < 2:
            messagebox.showerror("Error", "At least 2 players required!")
            return

        if len(names) != len(set(names)):
            messagebox.showerror("Error", "Player names must be unique!")
            return

        if any(len(name) > 20 for name in names):
            messagebox.showerror(
                "Error", "Player names must be 20 characters or less!")
            return

        self.result = names
        self.dialog.destroy()

    def _cancel_clicked(self):
        """Handle Cancel button click."""
        self.dialog.destroy()
