"""
Logging utilities for the Organ Attack card game.
Provides structured logging for game events, debugging, and error tracking.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up the game logger with console and optional file output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('organ_attack')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"Logging to file: {log_file}")
            
        except Exception as e:
            logger.warning(f"Could not create file handler for {log_file}: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def create_game_logger(game_id: str) -> logging.Logger:
    """
    Create a game-specific logger for detailed game event tracking.
    
    Args:
        game_id: Unique identifier for the game session
    
    Returns:
        Game-specific logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"game_{game_id}_{timestamp}.log"
    
    return setup_logger("DEBUG", str(log_file))

class GameEventLogger:
    """
    Specialized logger for game events with structured formatting.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_game_start(self, players: list, starting_player: str):
        """Log game initialization."""
        self.logger.info("="*60)
        self.logger.info("GAME STARTED")
        self.logger.info("="*60)
        self.logger.info(f"Players: {', '.join(players)}")
        self.logger.info(f"Starting player: {starting_player}")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    def log_turn_start(self, turn_number: int, player_name: str):
        """Log the start of a player's turn."""
        self.logger.info(f"TURN {turn_number}: {player_name}")
    
    def log_card_played(self, player: str, card: str, target_player: str = None, 
                       target_organ: str = None):
        """Log a card being played."""
        msg = f"{player} played '{card}'"
        if target_player and target_organ:
            msg += f" targeting {target_player}'s {target_organ}"
        elif target_player:
            msg += f" targeting {target_player}"
        self.logger.info(msg)
    
    def log_attack_result(self, attacker: str, defender: str, card: str, 
                         target_organ: str, success: bool, blocked_by: str = None):
        """Log the result of an attack."""
        if success:
            self.logger.info(f"ATTACK SUCCESS: {attacker}'s {card} destroyed {defender}'s {target_organ}")
        else:
            block_info = f" (blocked by {blocked_by})" if blocked_by else ""
            self.logger.info(f"ATTACK BLOCKED: {attacker}'s {card} vs {defender}'s {target_organ}{block_info}")
    
    def log_player_elimination(self, player_name: str, turn_number: int):
        """Log a player being eliminated."""
        self.logger.warning(f"PLAYER ELIMINATED: {player_name} on turn {turn_number}")
    
    def log_game_end(self, winner: str = None, turn_count: int = 0):
        """Log game completion."""
        self.logger.info("="*60)
        self.logger.info("GAME ENDED")
        self.logger.info("="*60)
        if winner:
            self.logger.info(f"Winner: {winner}")
        else:
            self.logger.info("No winner - all players eliminated")
        self.logger.info(f"Total turns: {turn_count}")
        self.logger.info(f"End time: {datetime.now().isoformat()}")
    
    def log_error(self, error_type: str, message: str, player: str = None):
        """Log game errors."""
        error_msg = f"ERROR [{error_type}]: {message}"
        if player:
            error_msg += f" (Player: {player})"
        self.logger.error(error_msg)
    
    def log_debug_info(self, context: str, details: dict):
        """Log debugging information."""
        self.logger.debug(f"DEBUG [{context}]: {details}")

def log_performance(func):
    """
    Decorator to log function performance.
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('organ_attack')
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"Performance: {func.__name__} took {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Performance: {func.__name__} failed after {duration:.3f}s - {e}")
            raise
    
    return wrapper

# Configure default logger on module import
default_logger = setup_logger()
