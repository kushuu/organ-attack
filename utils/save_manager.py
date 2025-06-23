"""
Save and load game state management for the Organ Attack card game.
Handles serialization of game state to/from JSON files.
"""

import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SaveManager:
    """Manages saving and loading game states."""

    def __init__(self, save_directory: str = "saves"):
        self.save_directory = Path(save_directory)
        self.save_directory.mkdir(exist_ok=True)

        # Create metadata file if it doesn't exist
        self.metadata_file = self.save_directory / "save_metadata.json"
        if not self.metadata_file.exists():
            self._initialize_metadata()

    def _initialize_metadata(self):
        """Initialize the save metadata file."""
        metadata = {
            "saves": {},
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info("Initialized save metadata file")
        except Exception as e:
            logger.error(f"Failed to initialize metadata: {e}")

    def save_game(self, filename: str, game_data: Dict[str, Any]) -> bool:
        """
        Save game state to a file.
        
        Args:
            filename: Name of the save file (without extension)
            game_data: Dictionary containing game state
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'

            save_path = self.save_directory / filename

            # Add metadata to game data
            save_data = {
                "metadata": {
                    "save_time": datetime.now().isoformat(),
                    "version": "1.0",
                    "game_type": "organ_attack"
                },
                "game_data": game_data
            }

            # Save as compressed JSON
            with gzip.open(str(save_path) + '.gz', 'wt', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2,
                          default=self._json_serializer)

            # Update metadata
            self._update_save_metadata(filename, game_data)

            logger.info(f"Game saved successfully to {save_path}.gz")
            return True

        except Exception as e:
            logger.error(f"Failed to save game: {e}")
            return False

    def load_game(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load game state from a file.
        
        Args:
            filename: Name of the save file
        
        Returns:
            Game data dictionary if successful, None otherwise
        """
        try:
            # Try both with and without .json extension
            if not filename.endswith('.json'):
                filename += '.json'

            save_path = self.save_directory / (filename + '.gz')

            if not save_path.exists():
                # Try without .gz extension (legacy support)
                save_path = self.save_directory / filename
                if not save_path.exists():
                    logger.error(f"Save file not found: {filename}")
                    return None

            # Load compressed JSON
            if str(save_path).endswith('.gz'):
                with gzip.open(save_path, 'rt', encoding='utf-8') as f:
                    save_data = json.load(f)
            else:
                with open(save_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)

            # Validate save data structure
            if not self._validate_save_data(save_data):
                logger.error("Invalid save data structure")
                return None

            logger.info(f"Game loaded successfully from {save_path}")
            return save_data.get("game_data", save_data)

        except Exception as e:
            logger.error(f"Failed to load game: {e}")
            return None

    def list_saves(self) -> List[Dict[str, Any]]:
        """
        List all available save files with metadata.
        
        Returns:
            List of save file information dictionaries
        """
        try:
            saves = []

            # Read metadata
            metadata = self._read_metadata()
            saved_games = metadata.get("saves", {})

            # List all save files in directory
            for save_file in self.save_directory.glob("*.json*"):
                filename = save_file.name
                if filename == "save_metadata.json":
                    continue

                # Remove .gz extension if present
                if filename.endswith('.gz'):
                    display_name = filename[:-3]  # Remove .gz
                else:
                    display_name = filename

                # Remove .json extension for display
                if display_name.endswith('.json'):
                    display_name = display_name[:-5]

                save_info = {
                    "filename": display_name,
                    "full_path": str(save_file),
                    "size": save_file.stat().st_size,
                    "modified": datetime.fromtimestamp(save_file.stat().st_mtime).isoformat()
                }

                # Add metadata if available
                if filename in saved_games:
                    save_info.update(saved_games[filename])

                saves.append(save_info)

            # Sort by modification time (newest first)
            saves.sort(key=lambda x: x.get("modified", ""), reverse=True)

            return saves

        except Exception as e:
            logger.error(f"Failed to list saves: {e}")
            return []

    def delete_save(self, filename: str) -> bool:
        """
        Delete a save file.
        
        Args:
            filename: Name of the save file to delete
        
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if not filename.endswith('.json'):
                filename += '.json'

            # Try to delete both compressed and uncompressed versions
            save_paths = [
                self.save_directory / (filename + '.gz'),
                self.save_directory / filename
            ]

            deleted = False
            for save_path in save_paths:
                if save_path.exists():
                    save_path.unlink()
                    deleted = True
                    logger.info(f"Deleted save file: {save_path}")

            if deleted:
                # Remove from metadata
                self._remove_from_metadata(filename)
                return True
            else:
                logger.warning(f"Save file not found: {filename}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete save: {e}")
            return False

    def _update_save_metadata(self, filename: str, game_data: Dict[str, Any]):
        """Update the save metadata file."""
        try:
            metadata = self._read_metadata()

            # Extract relevant game info
            players = []
            turn_count = 0
            current_player = ""

            if "players" in game_data:
                players = [p.get("name", "Unknown")
                           for p in game_data["players"]]

            if "turn_count" in game_data:
                turn_count = game_data["turn_count"]

            if "current_player_index" in game_data and players:
                current_index = game_data["current_player_index"]
                if 0 <= current_index < len(players):
                    current_player = players[current_index]

            # Update metadata
            metadata["saves"][filename] = {
                "saved_at": datetime.now().isoformat(),
                "players": players,
                "turn_count": turn_count,
                "current_player": current_player,
                "game_state": game_data.get("game_state", "Unknown")
            }

            metadata["last_updated"] = datetime.now().isoformat()

            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")

    def _remove_from_metadata(self, filename: str):
        """Remove a save from metadata."""
        try:
            metadata = self._read_metadata()

            if filename in metadata["saves"]:
                del metadata["saves"][filename]
                metadata["last_updated"] = datetime.now().isoformat()

                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to remove from metadata: {e}")

    def _read_metadata(self) -> Dict[str, Any]:
        """Read the save metadata file."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return {"saves": {}}

    def _validate_save_data(self, save_data: Dict[str, Any]) -> bool:
        """Validate the structure of save data."""
        try:
            # Check for required fields
            if "game_data" in save_data:
                game_data = save_data["game_data"]
            else:
                # Assume old format where entire dict is game data
                game_data = save_data

            # Basic validation
            required_fields = ["players", "current_player_index", "game_state"]
            for field in required_fields:
                if field not in game_data:
                    logger.warning(
                        f"Save data missing required field: {field}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating save data: {e}")
            return False

    def _json_serializer(self, obj):
        """Custom JSON serializer for special objects."""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return str(obj)

    def export_save(self, filename: str, export_path: str) -> bool:
        """
        Export a save file to a different location.
        
        Args:
            filename: Name of the save file to export
            export_path: Path where to export the file
        
        Returns:
            True if export successful, False otherwise
        """
        try:
            game_data = self.load_game(filename)
            if not game_data:
                return False

            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with open(export_file, 'w') as f:
                json.dump(game_data, f, indent=2,
                          default=self._json_serializer)

            logger.info(f"Save exported to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export save: {e}")
            return False

    def import_save(self, import_path: str, filename: str) -> bool:
        """
        Import a save file from an external location.
        
        Args:
            import_path: Path to the save file to import
            filename: Name to save the imported file as
        
        Returns:
            True if import successful, False otherwise
        """
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"Import file not found: {import_path}")
                return False

            with open(import_file, 'r') as f:
                game_data = json.load(f)

            # Validate imported data
            if not self._validate_save_data({"game_data": game_data}):
                logger.error("Invalid imported save data")
                return False

            return self.save_game(filename, game_data)

        except Exception as e:
            logger.error(f"Failed to import save: {e}")
            return False

    def cleanup_old_saves(self, max_saves: int = 50, max_age_days: int = 30):
        """
        Clean up old save files to prevent disk space issues.
        
        Args:
            max_saves: Maximum number of saves to keep
            max_age_days: Maximum age of saves in days
        """
        try:
            saves = self.list_saves()

            # Remove saves older than max_age_days
            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

            for save in saves:
                save_time = datetime.fromisoformat(save.get("modified", ""))
                if save_time.timestamp() < cutoff_date:
                    self.delete_save(save["filename"])
                    logger.info(f"Cleaned up old save: {save['filename']}")

            # If still too many saves, remove oldest ones
            remaining_saves = self.list_saves()
            if len(remaining_saves) > max_saves:
                excess_saves = remaining_saves[max_saves:]
                for save in excess_saves:
                    self.delete_save(save["filename"])
                    logger.info(f"Cleaned up excess save: {save['filename']}")

        except Exception as e:
            logger.error(f"Failed to cleanup old saves: {e}")
