"""
Dialog windows for the Organ Attack GUI.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from utils.save_manager import SaveManager


class NewGameDialog:
    """Dialog for setting up a new game."""

    def __init__(self, parent):
        self.parent = parent
        self.result: Optional[List[str]] = None
        self.player_entries: List[tk.Entry] = []

        self._create_dialog()

    def _create_dialog(self):
        """Create the new game dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("New Game Setup")
        self.dialog.geometry("400x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (350 // 2)
        self.dialog.geometry(f"400x350+{x}+{y}")

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


class LoadGameDialog:
    """Dialog for loading a saved game."""

    def __init__(self, parent):
        self.parent = parent
        self.result: Optional[str] = None
        self.save_manager = SaveManager()

        self._create_dialog()

    def _create_dialog(self):
        """Create the load game dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Load Saved Game")
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text="Load Saved Game",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # Saved games list
        list_frame = ttk.LabelFrame(main_frame, text="Saved Games")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Create treeview for saves
        columns = ('Name', 'Players', 'Turn', 'Saved')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        # Configure columns
        self.tree.heading('Name', text='Game Name')
        self.tree.heading('Players', text='Players')
        self.tree.heading('Turn', text='Turn')
        self.tree.heading('Saved', text='Saved At')

        self.tree.column('Name', width=150)
        self.tree.column('Players', width=100)
        self.tree.column('Turn', width=80)
        self.tree.column('Saved', width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load saved games
        self._load_saves()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM)

        load_button = ttk.Button(button_frame, text="Load Game",
                                 command=self._load_clicked)
        load_button.pack(side=tk.LEFT, padx=(0, 10))

        delete_button = ttk.Button(button_frame, text="Delete",
                                   command=self._delete_clicked)
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        refresh_button = ttk.Button(button_frame, text="Refresh",
                                    command=self._refresh_clicked)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(button_frame, text="Cancel",
                                   command=self._cancel_clicked)
        cancel_button.pack(side=tk.LEFT)

        # Bind double-click
        self.tree.bind('<Double-1>', lambda e: self._load_clicked())

        self.dialog.wait_window()

    def _load_saves(self):
        """Load the list of saved games."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get saved games
        saves = self.save_manager.list_saves()

        if not saves:
            # No saves found
            self.tree.insert('', tk.END, values=(
                'No saved games found', '', '', ''))
            return

        # Add saves to tree
        for save in saves:
            name = save.get('filename', 'Unknown')
            players = ', '.join(save.get('players', []))
            turn = str(save.get('turn_count', 0))
            saved_at = save.get('saved_at', '')

            # Format saved date
            if saved_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(
                        saved_at.replace('Z', '+00:00'))
                    saved_at = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass

            self.tree.insert('', tk.END, values=(
                name, players, turn, saved_at))

    def _load_clicked(self):
        """Handle Load button click."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Warning", "Please select a saved game to load!")
            return

        item = self.tree.item(selection[0])
        filename = item['values'][0]

        if filename == 'No saved games found':
            return

        self.result = filename
        self.dialog.destroy()

    def _delete_clicked(self):
        """Handle Delete button click."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Warning", "Please select a saved game to delete!")
            return

        item = self.tree.item(selection[0])
        filename = item['values'][0]

        if filename == 'No saved games found':
            return

        # Confirm deletion
        result = messagebox.askyesno("Confirm Delete",
                                     f"Are you sure you want to delete '{filename}'?")
        if result:
            success = self.save_manager.delete_save(filename)
            if success:
                self._refresh_clicked()
                messagebox.showinfo(
                    "Success", f"'{filename}' deleted successfully!")
            else:
                messagebox.showerror(
                    "Error", f"Failed to delete '{filename}'!")

    def _refresh_clicked(self):
        """Handle Refresh button click."""
        self._load_saves()

    def _cancel_clicked(self):
        """Handle Cancel button click."""
        self.dialog.destroy()
