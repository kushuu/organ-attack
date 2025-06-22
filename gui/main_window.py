"""
Main GUI window for the Organ Attack card game.
Provides the primary game interface with modern styling.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import List, Optional

from game.cards import Card
from game.engine import GameEngine
from game.player import Player
from gui.dialogs import LoadGameDialog, NewGameDialog
from gui.game_board import GameBoard
from gui.player_panel import PlayerPanel
from utils.logger import setup_logger

logger = setup_logger()

class MainWindow:
    """Main game window handling all GUI interactions."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Organ Attack - The Ultimate Survival Game")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
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
        self._create_menu()
        self._create_main_frame()
        self._create_status_bar()
        
        # Show start screen
        self._show_start_screen()
        
        # Bind events
        self._bind_events()
    
    def _configure_styles(self):
        """Configure ttk styles for modern appearance."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_color = '#2c3e50'
        fg_color = '#ecf0f1'
        accent_color = '#e74c3c'
        button_color = '#3498db'
        
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
        self.root.configure(bg=bg_color)
    
    def _create_menu(self):
        """Create the main menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Game menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="New Game", command=self._new_game)
        game_menu.add_command(label="Load Game", command=self._load_game)
        game_menu.add_separator()
        game_menu.add_command(label="Save Game", command=self._save_game)
        game_menu.add_separator()
        game_menu.add_command(label="Exit", command=self._quit_game)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="How to Play", command=self._show_rules)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_main_frame(self):
        """Create the main content frame."""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready to play Organ Attack!")
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
        self.root.bind('<Control-n>', lambda e: self._new_game())
        self.root.bind('<Control-s>', lambda e: self._save_game())
        self.root.bind('<Control-o>', lambda e: self._load_game())
        self.root.bind('<F1>', lambda e: self._show_rules())
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self._quit_game)
    
    def _new_game(self):
        """Start a new game."""
        dialog = NewGameDialog(self.root)
        if dialog.result:
            player_names = dialog.result
            try:
                self.engine = GameEngine(player_names)
                self._setup_game_interface()
                self._update_status("New game started!")
                logger.info(f"New game started with players: {player_names}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start game: {e}")
                logger.error(f"Failed to start new game: {e}")
    
    def _load_game(self):
        """Load a saved game."""
        dialog = LoadGameDialog(self.root)
        if dialog.result:
            try:
                success = self.engine.load_game(dialog.result)
                if success:
                    self._setup_game_interface()
                    self._update_status("Game loaded successfully!")
                    logger.info(f"Game loaded: {dialog.result}")
                else:
                    messagebox.showerror("Error", "Failed to load game file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load game: {e}")
                logger.error(f"Failed to load game: {e}")
    
    def _save_game(self):
        """Save the current game."""
        if not self.engine:
            messagebox.showwarning("Warning", "No game to save!")
            return
        
        filename = simpledialog.askstring("Save Game", "Enter save name:")
        if filename:
            try:
                success = self.engine.save_game(filename)
                if success:
                    self._update_status(f"Game saved as {filename}")
                    messagebox.showinfo("Success", f"Game saved as {filename}")
                else:
                    messagebox.showerror("Error", "Failed to save game")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save game: {e}")
    
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
        self.turn_label.config(text=f"Turn: {current_player.name} | Phase: {game_state}")
        
        # Check for game over
        if self.engine.is_game_over():
            self._show_game_over()
    
    def _show_game_over(self):
        """Display game over screen."""
        winner = self.engine.get_winner()
        if winner:
            message = f"Game Over!\n\n{winner.name} wins!"
        else:
            message = "Game Over!\n\nNo winner - all players eliminated!"
        
        result = messagebox.askyesno(
            "Game Over", f"{message}\n\nWould you like to start a new game?")
        if result:
            self._new_game()
        else:
            self._show_start_screen()
    
    def _show_rules(self):
        """Display game rules in a popup window."""
        rules_window = tk.Toplevel(self.root)
        rules_window.title("How to Play Organ Attack")
        rules_window.geometry("600x500")
        rules_window.resizable(False, False)
        
        # Make window modal
        rules_window.transient(self.root)
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
        
        rules_text = """
ORGAN ATTACK - How to Play

OBJECTIVE:
Be the last player with at least one organ remaining!

SETUP:
• Each player starts with 6 organs: Heart, Brain, Lungs, Kidneys, Eyes, and Liver
• Players receive 5 cards to start
• The deck contains Attack, Defense, Action, and Wildcard cards

GAMEPLAY:
Each turn consists of several phases:

1. DRAW PHASE
   • Draw 1 card from the deck

2. PLAY PHASE  
   • Play 1 card from your hand
   • Choose targets if required

3. DEFEND PHASE (if attacked)
   • Defending player can play defense cards
   • Or skip to take the damage

4. DISCARD PHASE
   • Discard down to 5 cards if over the limit

CARD TYPES:

ATTACK CARDS
• Target specific organs on other players
• Examples: Heart Attack, Brain Freeze, Liver Failure

DEFENSE CARDS
• Block incoming attacks
• Examples: Medical Kit, Surgery, Vaccination

ACTION CARDS
• Special effects and abilities
• Examples: Organ Transplant, Medical Research, Anesthesia

WILDCARD CARDS
• Flexible cards with powerful effects
• Examples: Medical Mystery, Pandemic

WINNING:
• Players are eliminated when all their organs are removed
• Last player with organs remaining wins!

TIPS:
• Protect vital organs (Heart and Brain) with defense cards
• Use action cards strategically
• Watch other players' organ counts
• Save defense cards for crucial moments
        """
        
        text_widget.insert(tk.END, rules_text.strip())
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        close_btn = ttk.Button(rules_window, text="Close", 
                              command=rules_window.destroy)
        close_btn.pack(pady=10)
    
    def _show_about(self):
        """Display about dialog."""
        about_text = """Organ Attack
The Ultimate Survival Game

Version 1.0

A strategic card game where players battle to be the last survivor by attacking opponents' organs while defending their own.

Built with Python and tkinter.
        """
        messagebox.showinfo("About Organ Attack", about_text)
    
    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.root.after(3000, lambda: self.status_label.config(text="Ready"))
    
    def _quit_game(self):
        """Quit the application."""
        if self.engine and not self.engine.is_game_over():
            result = messagebox.askyesno("Quit Game", 
                                       "A game is in progress. Do you want to save before quitting?")
            if result:
                self._save_game()
        
        self.root.quit()
        self.root.destroy()
    
    def play_card(self, card: Card, target_player: Optional[Player] = None, 
                  target_organ: Optional[str] = None):
        """Handle card play from GUI."""
        if not self.engine:
            return
        
        current_player = self.engine.get_current_player()
        result = self.engine.play_card(current_player, card, target_player, target_organ)
        
        if result['success']:
            self._update_status(f"Played {card.name}")
            self._update_game_display()
        else:
            messagebox.showerror("Invalid Play", result.get('reason', 'Cannot play this card'))
    
    def advance_turn(self):
        """Advance to the next turn phase."""
        if self.engine:
            self.engine.advance_turn()
            self._update_game_display()
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()

def main():
    """Main entry point for the GUI application."""
    app = MainWindow()
    app.run()

if __name__ == "__main__":
    main()