import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from game.game_board import GameBoard
from game.game_engine import GameEngine
from gui.dialogs import NewGameDialog
from gui.player_panel import PlayerPanel
from game.models import GameState


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Organ Attack - The Ultimate Survival Game")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Game state
        self.engine: Optional[GameEngine] = None
        self.game_board: Optional[GameBoard] = None
        self.player_panels: List[PlayerPanel] = []

        # GUI elements
        self.main_frame = None
        self.menu_frame = None
        self.game_frame = None
        self.status_bar = None

        # Configure styles
        self._configure_styles()

        # Setup GUI
        self._create_main_frame()
        self._create_status_bar()

        # Show start screen
        self._show_start_screen()

        # Bind events
        self._bind_events()

    def _new_game(self):
        """Start a new game."""
        dialog = NewGameDialog(self)
        if dialog.result:
            player_names = dialog.result
            try:
                self.engine = GameEngine(player_names)
                print("Game engine initialized")
                self._setup_game_interface()
                self._update_status("New game started!")
                print(f"New game started with players: {player_names}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start game: {e}")
                print(f"Failed to start new game: {e}")

    def _setup_game_interface(self):
        """Setup the main game interface."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Create game frame
        self.game_frame = ttk.Frame(self.main_frame)
        self.game_frame.pack(fill=tk.BOTH, expand=True)

        # Create game board
        self.game_board = GameBoard(self.game_frame, self.engine, self)
        self.game_board.pack(fill=tk.BOTH, expand=True)

        # Update display
        self._update_game_display()

    def _update_game_display(self):
        """Update all game display elements."""
        if not self.engine:
            return

        # Update game board
        if self.game_board:
            self.game_board.update_display()

        # Update status
        current_player = self.engine.get_current_player()
        game_state = self.engine.game_state.name
        self.turn_label.config(
            text=f"Turn: {current_player.name} | Phase: {game_state}")

        # Check for game over
        if self.engine.is_game_over():
            self._show_game_over()

    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.root.after(3000, lambda: self.status_label.config(text="Ready"))

    def _save_game(self):
        """Save the current game state."""
        # TODO: Implement save game functionality
        messagebox.showinfo(
            "Save Game", "Save game functionality not implemented yet.")

    def _load_game(self):
        """Load a saved game."""
        # TODO: Implement load game functionality
        messagebox.showinfo(
            "Load Game", "Load game functionality not implemented yet.")

    def _show_rules(self):
        """Display game rules in a popup window."""
        rules_window = tk.Toplevel(self)
        rules_window.title("How to Play Organ Attack")
        rules_window.geometry("600x500")
        rules_window.resizable(False, False)

        # Make window modal
        rules_window.transient(self)
        rules_window.grab_set()

        # Create scrollable text
        text_frame = ttk.Frame(rules_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              font=('Arial', 11), bg='#ecf0f1', fg='#2c3e50')
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=text_widget.yview)

        rules_text = open("rules.txt", "r").read()

        text_widget.insert(tk.END, rules_text.strip())
        text_widget.config(state=tk.DISABLED)

        # Close button
        close_btn = ttk.Button(rules_window, text="Close",
                               command=rules_window.destroy)
        close_btn.pack(pady=10)

    def _show_about(self):
        """Display about dialog."""
        about_text = open("about.txt", "r").read()
        messagebox.showinfo("About Organ Attack", about_text)

    def _quit_game(self):
        """Quit the application."""
        # TODO: Add save game functionality
        # if self.engine and not self.engine.is_game_over():
        #     result = messagebox.askyesno("Quit Game",
        #                                  "A game is in progress. Do you want to save before quitting?")
        #     if result:
        #         self._save_game()

        self.quit()
        self.destroy()

    def _create_main_frame(self):
        """Create the main content frame."""
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(
            self.status_bar, text="Ready to play Organ Attack!")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Turn indicator
        self.turn_label = ttk.Label(self.status_bar, text="")
        self.turn_label.pack(side=tk.RIGHT, padx=5)

    def _show_start_screen(self):
        """Display the initial start screen."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Create start screen
        start_frame = ttk.Frame(self.main_frame)
        start_frame.pack(expand=True, fill=tk.BOTH)

        # Title
        title_label = ttk.Label(
            start_frame, text="ORGAN ATTACK", style='Title.TLabel')
        title_label.pack(pady=50)

        subtitle_label = ttk.Label(
            start_frame, text="The Ultimate Survival Game",
            style='Heading.TLabel')
        subtitle_label.pack(pady=10)

        # Buttons
        button_frame = ttk.Frame(start_frame)
        button_frame.pack(pady=50)

        new_game_btn = ttk.Button(
            button_frame, text="New Game",
            command=self._new_game, style='Game.TButton')
        new_game_btn.pack(pady=10, ipadx=20)

        load_game_btn = ttk.Button(
            button_frame, text="Load Game",
            command=self._load_game, style='Game.TButton')
        load_game_btn.pack(pady=10, ipadx=20)

        rules_btn = ttk.Button(
            button_frame, text="How to Play",
            command=self._show_rules, style='Game.TButton')
        rules_btn.pack(pady=10, ipadx=20)

        quit_btn = ttk.Button(
            button_frame, text="Quit",
            command=self._quit_game, style='Game.TButton')
        quit_btn.pack(pady=10, ipadx=20)

    def _bind_events(self):
        """Bind keyboard and window events."""
        self.bind('<Control-n>', lambda e: self._new_game())
        self.bind('<Control-s>', lambda e: self._save_game())
        self.bind('<Control-o>', lambda e: self._load_game())
        self.bind('<F1>', lambda e: self._show_rules())

        # Window close event
        self.protocol("WM_DELETE_WINDOW", self._quit_game)

    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.after(3000, lambda: self.status_label.config(text="Ready"))

    def _configure_styles(self):
        """Configure ttk styles for modern appearance."""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        bg_color = '#2c3e50'
        fg_color = '#ecf0f1'
        accent_color = '#e74c3c'

        # Configure styles
        style.configure('Title.TLabel',
                        font=('Arial', 24, 'bold'),
                        foreground=accent_color,
                        background=bg_color)

        style.configure('Heading.TLabel',
                        font=('Arial', 14, 'bold'),
                        foreground=fg_color,
                        background=bg_color)

        style.configure('Game.TButton',
                        font=('Arial', 12),
                        padding=10)

        style.configure('Card.TFrame',
                        relief='raised',
                        borderwidth=2)

        # Configure root window
        self.configure(bg=bg_color)

    def play_card(self, card, target_player=None, target_organ=None):
        """Handle playing a card from the UI."""
        current_player = self.engine.get_current_player()
        if card not in current_player.hand:
            self._update_status("Card not in hand!")
            return

        # Remove card from hand
        current_player.remove_card_from_hand(card)

        # Process card effects
        results = self.engine.effect_processor.process_card_effects(
            card, current_player, target_player, target_organ
        )

        # Optionally, add card to discard pile
        self.engine.discard_pile.append(card)

        # Update status and UI
        self._update_status(f"Played {card.name}")
        self._update_game_display()

    def advance_turn(self):
        """Advance to the next non-eliminated player, set state to PLAY, and refresh hand to 5 cards. End game if only 1 active player remains."""
        if not self.engine:
            return
        # Remove vaccination (protection) from all organs protected by 'Vaccination'
        for player in self.engine.players:
            for organ in player.organs.values():
                if organ.is_protected and organ.protection_source == 'Vaccination':
                    organ.is_protected = False
                    organ.protection_source = None
        # Check for game end
        active_players = self.engine.get_active_players()
        if len(active_players) == 1:
            self.engine.game_state = GameState.DONE
            winner = active_players[0]
            self._update_status(f"Game over! Winner: {winner.name}")
            self._update_game_display()
            return
        num_players = len(self.engine.players)
        for _ in range(num_players):
            self.engine.current_player_index = (
                self.engine.current_player_index + 1) % num_players
            next_player = self.engine.get_current_player()
            if not next_player.is_eliminated():
                break
        # Refresh hand to 5 cards
        current_player = self.engine.get_current_player()
        while len(current_player.hand) < 5:
            card = self.engine.draw_card_for_player(current_player)
            if not card:
                break  # No more cards to draw
        self.engine.game_state = GameState.PLAY
        self._update_status(
            f"It's now {self.engine.get_current_player().name}'s turn! (Hand refreshed to {len(current_player.hand)} cards)")
        self._update_game_display()

    def _show_game_over(self):
        winner = None
        if self.engine:
            active_players = self.engine.get_active_players()
            if len(active_players) == 1:
                winner = active_players[0].name
        message = f"Game Over!\nWinner: {winner}" if winner else "Game Over!"
        tk.messagebox.showinfo("Game Over", message)


def main():
    app = MainWindow()
    app.mainloop()
