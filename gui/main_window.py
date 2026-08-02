import tkinter as tk
import asyncio
import threading
from tkinter import messagebox, ttk
from typing import List, Optional

from game.game_board import GameBoard
from game.game_engine import GameEngine
from gui.dialogs import NewGameDialog, HostGameDialog, JoinGameDialog
from gui.player_panel import PlayerPanel
from game.models import GameState

try:
    from server.client import OnlineGameManager
    ONLINE_AVAILABLE = True
except ImportError:
    ONLINE_AVAILABLE = False


_asyncio_thread: Optional[threading.Thread] = None
_asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_ready = threading.Event()


def _start_asyncio_thread():
    """Start the asyncio event loop in a background thread."""
    global _asyncio_loop, _asyncio_thread

    if _asyncio_thread and _asyncio_thread.is_alive():
        return

    def run_loop():
        global _asyncio_loop
        _asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_asyncio_loop)
        _loop_ready.set()
        _asyncio_loop.run_forever()

    _asyncio_thread = threading.Thread(target=run_loop, daemon=True)
    _asyncio_thread.start()
    _loop_ready.wait(timeout=2)


def _run_async(coro):
    """Run a coroutine in the asyncio thread."""
    global _asyncio_loop
    if _asyncio_loop is None:
        _start_asyncio_thread()

    try:
        future = asyncio.run_coroutine_threadsafe(coro, _asyncio_loop)
        result = future.result(timeout=10)
        return result
    except Exception as e:
        logger.error(f"Async error: {e}")
        raise


import logging
logger = logging.getLogger(__name__)

RULES_TEXT = """ORGAN ATTACK - How to Play

GOAL:
Be the last player with organs remaining!

SETUP:
- Each player starts with 6 random organs and 5 cards
- Take turns clockwise

ON YOUR TURN:
1. Draw 1 card from the deck
2. Play cards from your hand (optional)
3. End your turn

CARD TYPES:
- ATTACK (Red): Remove an opponent's organ. Each attack targets a specific organ type.
- DEFENSE (Green): Protect your organs or block attacks.
- ACTION (Blue): Special abilities like drawing extra cards, skipping turns, or stealing organs.
- WILDCARD (Purple): Versatile cards with various effects.

PLAYING CARDS:
- Click a card in your hand to play it
- Some cards require selecting a target player and organ
- Defense cards can be played in response to attacks

PROTECTION:
- Vaccination protects an organ from attacks for 2 full rounds (all players × 2 turns)
- Protected organs cannot be removed until protection is stripped

ELIMINATION:
- When a player loses all organs, they are eliminated
- The last player standing wins!

MULTIPLAYER:
- Host a game and share the 6-character code
- Other players join using the code
- All players take turns in order"""

ABOUT_TEXT = """ORGAN ATTACK v0.1.0
The Ultimate Card Game of Survival

A multiplayer card game where players compete to be the last one with organs remaining. Attack opponents, defend your own, and outlast everyone else!

Created by Kushagra Soni"""


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

        # Online game state
        self.online_manager: Optional[OnlineGameManager] = None
        self.is_online_game: bool = False
        self.lobby_window: Optional[tk.Toplevel] = None

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
        """Start a new local game."""
        dialog = NewGameDialog(self)
        if dialog.result:
            player_names = dialog.result
            try:
                self.engine = GameEngine(player_names)
                self.is_online_game = False
                self._setup_game_interface()
                self._update_status("New game started!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start game: {e}")

    def _host_game(self):
        """Host an online game."""
        if not ONLINE_AVAILABLE:
            messagebox.showerror("Error", "Online multiplayer is not available. Please install the required dependencies.")
            return

        dialog = HostGameDialog(self)
        if dialog.result:
            try:
                self._update_status("Connecting to server...")

                _start_asyncio_thread()
                self.online_manager = OnlineGameManager(dialog.result["server_url"])

                self.online_manager.on_game_started = self._on_game_started
                self.online_manager.on_game_state_update = self._on_game_state_update

                _run_async(self.online_manager.host_game(dialog.result["player_name"]))

                self.is_online_game = True
                self._update_status("Lobby created! Waiting for players...")

                def show_lobby():
                    self._show_lobby_window()
                    self.update()
                    if self.lobby_window:
                        self.lobby_window.update()

                self.after(800, show_lobby)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to host game: {e}")

    def _join_game(self):
        """Join an online game."""
        if not ONLINE_AVAILABLE:
            messagebox.showerror("Error", "Online multiplayer is not available. Please install the required dependencies.")
            return

        dialog = JoinGameDialog(self)
        if dialog.result:
            try:
                server_url = dialog.result["server_url"]
                player_name = dialog.result["player_name"]
                code = dialog.result["code"]

                self._update_status("Connecting to server...")

                _start_asyncio_thread()
                self.online_manager = OnlineGameManager(server_url)

                self.online_manager.on_game_started = self._on_game_started
                self.online_manager.on_game_state_update = self._on_game_state_update

                _run_async(self.online_manager.join_game(code, player_name))

                self.is_online_game = True
                self._show_lobby_window()
                self._update_status("Joined lobby! Waiting for game to start...")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to join game: {e}")

    def _show_lobby_window(self):
        """Show the lobby window for online games."""
        if self.lobby_window:
            self.lobby_window.destroy()

        self.lobby_window = tk.Toplevel(self)
        self.lobby_window.title("Game Lobby")
        self.lobby_window.geometry("400x300")
        self.lobby_window.transient(self)

        main_frame = ttk.Frame(self.lobby_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_label = ttk.Label(main_frame, text="Waiting for Players",
                                font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        self.lobby_code_label = ttk.Label(main_frame, text="",
                                          font=('Arial', 12))
        self.lobby_code_label.pack(pady=(0, 10))

        players_label = ttk.Label(main_frame, text="Players:",
                                  font=('Arial', 11))
        players_label.pack(anchor=tk.W)

        self.players_listbox = tk.Listbox(main_frame, font=('Arial', 11))
        self.players_listbox.pack(fill=tk.BOTH, expand=True, pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM)

        is_host = False
        if self.online_manager and self.online_manager.client:
            is_host = self.online_manager.client.is_host

        if is_host:
            start_button = ttk.Button(button_frame, text="Start Game",
                                      command=self._start_online_game)
            start_button.pack(side=tk.LEFT, padx=(0, 10))

        leave_button = ttk.Button(button_frame, text="Leave Lobby",
                                  command=self._leave_lobby)
        leave_button.pack(side=tk.LEFT)

        self._update_lobby_display()
        self.lobby_window.protocol("WM_DELETE_WINDOW", self._leave_lobby)

    def _update_lobby_display(self):
        """Update the lobby display with current players."""
        if not self.lobby_window or not self.online_manager:
            return

        code = self.online_manager.client.current_lobby_code or "------"
        self.lobby_code_label.config(text=f"Game Code: {code}")

        self.players_listbox.delete(0, tk.END)
        if self.online_manager.current_players:
            for player in self.online_manager.current_players:
                name = player.get("name", "Unknown")
                host_tag = " (Host)" if player.get("is_host") else ""
                self.players_listbox.insert(tk.END, f"{name}{host_tag}")
        else:
            self.players_listbox.insert(tk.END, "Waiting for players...")

        self.lobby_window.after(1000, self._update_lobby_display)

    def _start_online_game(self):
        """Start the online game."""
        if self.online_manager and self.online_manager.client.is_host:
            _run_async(self.online_manager.client.start_game())

    def _on_game_started(self, data):
        """Called when game starts from server."""
        self._update_status("Game started!")

        if self.lobby_window:
            self.lobby_window.destroy()
            self.lobby_window = None

        self._setup_online_game_interface(data.get("game_state", {}))

    def _on_game_state_update(self, game_state):
        """Called when game state updates from server."""
        self._update_game_display_from_state(game_state)

    def _setup_online_game_interface(self, game_state: dict):
        """Setup the game interface for online play."""
        self.engine = GameEngine.from_dict(game_state)
        self._setup_game_interface()
        self._update_status("Playing online game!")

    def _update_game_display_from_state(self, game_state: dict):
        """Update game display from server-synced state."""
        if not self.engine or not game_state:
            return

        self.engine.current_player_index = game_state.get("current_player_index", 0)
        self.engine.turn_count = game_state.get("turn_count", 0)

        # Restore player states
        for i, player_data in enumerate(game_state.get("players", [])):
            if i < len(self.engine.players):
                engine_player = self.engine.players[i]
                # Update organs
                for organ_type, org_data in player_data.get("organs", {}).items():
                    if organ_type in engine_player.organs:
                        organ = engine_player.organs[organ_type]
                        organ.is_removed = org_data.get("is_removed", False)
                        organ.is_protected = org_data.get("is_protected", False)
                        organ.protection_source = org_data.get("protection_source")
                # Update hand
                engine_player.hand = []
                for card_data in player_data.get("hand", []):
                    from game.models import Card, CardType
                    card = Card(
                        id=card_data["id"],
                        name=card_data["name"],
                        type=CardType(card_data["type"]),
                        description=card_data.get("description", "")
                    )
                    engine_player.hand.append(card)
                # Update status
                from game.models import PlayerStatus
                engine_player.status = PlayerStatus(player_data.get("status", "active"))
                engine_player.skip_next_turn = player_data.get("skip_next_turn", False)

        # Update game state
        gs = game_state.get("game_state")
        if gs is not None:
            try:
                self.engine.game_state = GameState(gs)
            except ValueError:
                pass

        # Update display
        if self.game_board:
            self.game_board.update_display()

        current_player = self.engine.get_current_player()
        if hasattr(self, 'turn_label') and self.turn_label:
            self.turn_label.config(
                text=f"Turn: {current_player.name} | Phase: {self.engine.game_state.name}")

    def _leave_lobby(self):
        """Leave the current lobby."""
        if self.online_manager:
            try:
                _run_async(self.online_manager.leave_game())
            except Exception:
                pass

        if self.lobby_window:
            self.lobby_window.destroy()
            self.lobby_window = None

        self.is_online_game = False
        self.online_manager = None
        self._update_status("Left lobby")

    def _setup_game_interface(self):
        """Setup the main game interface."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.game_frame = ttk.Frame(self.main_frame)
        self.game_frame.pack(fill=tk.BOTH, expand=True)

        self.game_board = GameBoard(self.game_frame, self.engine, self)
        self.game_board.pack(fill=tk.BOTH, expand=True)

        self._update_game_display()

    def _update_game_display(self):
        """Update all game display elements."""
        if not self.engine:
            return

        if self.game_board:
            self.game_board.update_display()

        current_player = self.engine.get_current_player()
        game_state = self.engine.game_state.name
        self.turn_label.config(
            text=f"Turn: {current_player.name} | Phase: {game_state}")

        if self.engine.is_game_over():
            self._show_game_over()

    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.after(3000, lambda: self.status_label.config(text="Ready"))

    def _save_game(self):
        """Save the current game state."""
        messagebox.showinfo(
            "Save Game", "Save game functionality not implemented yet.")

    def _load_game(self):
        """Load a saved game."""
        messagebox.showinfo(
            "Load Game", "Load game functionality not implemented yet.")

    def _show_rules(self):
        """Display game rules in a popup window."""
        rules_window = tk.Toplevel(self)
        rules_window.title("How to Play Organ Attack")
        rules_window.geometry("600x500")
        rules_window.resizable(False, False)

        rules_window.transient(self)
        rules_window.grab_set()

        text_frame = ttk.Frame(rules_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              font=('Arial', 11), bg='#ecf0f1', fg='#2c3e50')
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=text_widget.yview)

        text_widget.insert(tk.END, RULES_TEXT)
        text_widget.config(state=tk.DISABLED)

        close_btn = ttk.Button(rules_window, text="Close",
                               command=rules_window.destroy)
        close_btn.pack(pady=10)

    def _show_about(self):
        """Display about dialog."""
        messagebox.showinfo("About Organ Attack", ABOUT_TEXT)

    def _quit_game(self):
        """Quit the application."""
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

        self.turn_label = ttk.Label(self.status_bar, text="")
        self.turn_label.pack(side=tk.RIGHT, padx=5)

    def _show_start_screen(self):
        """Display the initial start screen."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        start_frame = ttk.Frame(self.main_frame)
        start_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(
            start_frame, text="ORGAN ATTACK", style='Title.TLabel')
        title_label.pack(pady=50)

        subtitle_label = ttk.Label(
            start_frame, text="The Ultimate Survival Game",
            style='Heading.TLabel')
        subtitle_label.pack(pady=10)

        button_frame = ttk.Frame(start_frame)
        button_frame.pack(pady=50)

        new_game_btn = ttk.Button(
            button_frame, text="New Game",
            command=self._new_game, style='Game.TButton')
        new_game_btn.pack(pady=10, ipadx=20)

        if ONLINE_AVAILABLE:
            host_game_btn = ttk.Button(
                button_frame, text="Host Game",
                command=self._host_game, style='Game.TButton')
            host_game_btn.pack(pady=10, ipadx=20)

            join_game_btn = ttk.Button(
                button_frame, text="Join Game",
                command=self._join_game, style='Game.TButton')
            join_game_btn.pack(pady=10, ipadx=20)

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

        self.protocol("WM_DELETE_WINDOW", self._quit_game)

    def _configure_styles(self):
        """Configure ttk styles for modern appearance."""
        style = ttk.Style()
        style.theme_use('clam')

        bg_color = '#2c3e50'
        fg_color = '#ecf0f1'
        accent_color = '#e74c3c'

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

        self.configure(bg=bg_color)

    def play_card(self, card, target_player=None, target_organ=None):
        """Handle playing a card from the UI."""
        current_player = self.engine.get_current_player()
        if card not in current_player.hand:
            self._update_status("Card not in hand!")
            return

        if self.is_online_game and self.online_manager:
            # Send action to server
            target_name = target_player.name if target_player else None
            _run_async(self.online_manager.play_card(
                current_player.name, card.id, target_name, target_organ
            ))
        else:
            # Local game: process directly
            current_player.remove_card_from_hand(card)
            results = self.engine.effect_processor.process_card_effects(
                card, current_player, target_player, target_organ
            )
            self.engine.discard_pile.append(card)

        self._update_status(f"Played {card.name}")
        self._update_game_display()

    def draw_card(self):
        """Handle draw card action."""
        current_player = self.engine.get_current_player()

        if self.is_online_game and self.online_manager:
            _run_async(self.online_manager.draw_card(current_player.name))
        else:
            card = self.engine.draw_card_for_player(current_player)
            if card:
                self._update_status(f"Drew {card.name}")
            else:
                self._update_status("No cards left to draw")

        self._update_game_display()

    def advance_turn(self):
        """Advance to the next player's turn."""
        if not self.engine:
            return

        if self.is_online_game and self.online_manager:
            _run_async(self.online_manager.end_turn(
                self.engine.get_current_player().name
            ))
        else:
            self._advance_turn_local()

        self._update_game_display()

    def _advance_turn_local(self):
        """Advance turn for local games."""
        # Remove non-permanent protections and expired Vaccination protections
        for player in self.engine.players:
            for organ in player.organs.values():
                if organ.is_protected:
                    # Strip non-Vaccination protections immediately
                    if organ.protection_source and organ.protection_source != 'Vaccination':
                        organ.is_protected = False
                        organ.protection_source = None
                        organ.protection_expires_at = None
                    # Strip Vaccination protection if it has expired
                    elif organ.protection_source == 'Vaccination' and organ.protection_expires_at is not None:
                        if self.engine.turn_count >= organ.protection_expires_at:
                            organ.is_protected = False
                            organ.protection_source = None
                            organ.protection_expires_at = None

        # Check for game end
        active_players = self.engine.get_active_players()
        if len(active_players) == 1:
            self.engine.game_state = GameState.DONE
            winner = active_players[0]
            self._update_status(f"Game over! Winner: {winner.name}")
            self._update_game_display()
            return

        # Advance to next non-eliminated player
        num_players = len(self.engine.players)
        for _ in range(num_players):
            self.engine.current_player_index = (
                self.engine.current_player_index + 1) % num_players
            next_player = self.engine.get_current_player()
            if not next_player.is_eliminated():
                break

        # Draw cards to replenish hand to 5
        current_player = self.engine.get_current_player()
        while len(current_player.hand) < 5:
            card = self.engine.draw_card_for_player(current_player)
            if not card:
                break

        # Reset turn counters
        current_player.reset_turn_counters()

        self.engine.game_state = GameState.PLAY
        self.engine.turn_count += 1

        self._update_status(
            f"It's now {current_player.name}'s turn!")

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
