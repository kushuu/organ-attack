"""
Client module for online multiplayer gameplay.
Handles connecting to server, joining/creating lobbies, and game communication.
Sends actions to the server and receives state updates.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class GameClient:
    """WebSocket client for connecting to the game server."""

    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.player_id: Optional[str] = None
        self.is_host: bool = False
        self.current_lobby_code: Optional[str] = None
        self._listeners: Dict[str, List[Callable]] = {
            "connected": [],
            "disconnected": [],
            "lobby_created": [],
            "joined_lobby": [],
            "player_joined": [],
            "player_left": [],
            "player_ready": [],
            "game_started": [],
            "game_state": [],
            "game_state_update": [],
            "game_action": [],
            "lobby_info": [],
            "lobby_update": [],
            "error": [],
        }
        self._receive_task: Optional[asyncio.Task] = None

    def on(self, event: str, callback: Callable):
        """Register an event listener."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def _emit(self, event: str, data: Any):
        """Emit an event to all listeners."""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in {event} callback: {e}")

    async def connect(self) -> bool:
        """Connect to the game server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._emit("connected", {})
            logger.info(f"Connected to {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self._emit("disconnected", {})
        logger.info("Disconnected from server")

    async def _receive_loop(self):
        """Receive messages from the server."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message}")
                    continue

                msg_type = data.get("type", "unknown")
                logger.debug(f"Received: {msg_type}")

                if msg_type == "lobby_created":
                    self.player_id = data.get("player_id")
                    self.is_host = data.get("is_host", False)
                    self.current_lobby_code = data.get("code")
                    self._emit("lobby_created", data)

                elif msg_type == "joined_lobby":
                    self.player_id = data.get("player_id")
                    self.is_host = data.get("is_host", False)
                    self.current_lobby_code = data.get("code")
                    self._emit("joined_lobby", data)

                elif msg_type == "player_joined":
                    self._emit("player_joined", data)

                elif msg_type == "player_left":
                    self._emit("player_left", data)

                elif msg_type == "player_ready":
                    self._emit("player_ready", data)

                elif msg_type == "game_started":
                    self._emit("game_started", data)

                elif msg_type == "game_state":
                    self._emit("game_state", data)

                elif msg_type == "game_state_update":
                    self._emit("game_state_update", data)

                elif msg_type == "game_action":
                    self._emit("game_action", data)

                elif msg_type == "lobby_info":
                    self._emit("lobby_info", data)

                elif msg_type == "lobby_update":
                    self._emit("lobby_update", data)

                elif msg_type == "error":
                    self._emit("error", data)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed")
            self._emit("disconnected", {})

    async def _send(self, message: dict):
        """Send a message to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def create_lobby(self, player_name: str) -> bool:
        """Create a new game lobby."""
        return await self._send({
            "type": "create_lobby",
            "player_name": player_name
        })

    async def join_lobby(self, code: str, player_name: str) -> bool:
        """Join an existing lobby by code."""
        code = code.upper().strip()
        return await self._send({
            "type": "join_lobby",
            "code": code,
            "player_name": player_name
        })

    async def leave_lobby(self):
        """Leave the current lobby."""
        return await self._send({
            "type": "leave_lobby"
        })

    async def set_ready(self, ready: bool):
        """Set player ready status."""
        return await self._send({
            "type": "player_ready",
            "ready": ready
        })

    async def start_game(self):
        """Start the game (host only)."""
        return await self._send({
            "type": "start_game"
        })

    async def send_game_action(self, action: str, data: Dict[str, Any]):
        """Send a game action to the server for processing."""
        return await self._send({
            "type": "game_action",
            "action": action,
            "data": data
        })

    async def draw_card(self, player_name: str):
        """Send draw card action to server."""
        return await self.send_game_action("draw_card", {"player_name": player_name})

    async def play_card(self, player_name: str, card_id: str, target_player: str = None, target_organ: str = None):
        """Send play card action to server."""
        return await self.send_game_action("play_card", {
            "player_name": player_name,
            "card_id": card_id,
            "target_player": target_player,
            "target_organ": target_organ
        })

    async def end_turn(self, player_name: str):
        """Send end turn action to server."""
        return await self.send_game_action("end_turn", {"player_name": player_name})

    async def get_lobby_info(self):
        """Get current lobby information."""
        return await self._send({
            "type": "get_lobby_info"
        })

    async def get_game_state(self):
        """Get current game state."""
        return await self._send({
            "type": "get_game_state"
        })

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.websocket is not None and self.websocket.open

    @property
    def in_lobby(self) -> bool:
        """Check if player is in a lobby."""
        return self.current_lobby_code is not None


class OnlineGameManager:
    """Manages online game sessions using the GameClient."""

    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.client = GameClient(server_url)
        self._setup_callbacks()
        self.current_players: List[Dict[str, Any]] = []
        self.game_state: Dict[str, Any] = {}
        self.current_player_name: str = ""
        self.on_game_started: Optional[Callable] = None
        self.on_game_state_update: Optional[Callable] = None

    def _setup_callbacks(self):
        """Setup client callbacks."""
        self.client.on("connected", self._on_connected)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("lobby_created", self._on_lobby_created)
        self.client.on("joined_lobby", self._on_joined_lobby)
        self.client.on("player_joined", self._on_player_joined)
        self.client.on("player_left", self._on_player_left)
        self.client.on("player_ready", self._on_player_ready)
        self.client.on("game_started", self._on_game_started)
        self.client.on("game_state", self._on_game_state)
        self.client.on("game_state_update", self._on_game_state_update)
        self.client.on("lobby_info", self._on_lobby_info)
        self.client.on("lobby_update", self._on_lobby_update)
        self.client.on("error", self._on_error)

    def _on_connected(self, data):
        logger.info("Connected to server")

    def _on_disconnected(self, data):
        logger.info("Disconnected from server")

    def _on_lobby_created(self, data):
        logger.info(f"Lobby created: {data.get('code')}")
        players_data = data.get("players", [])
        if players_data:
            self.current_players = players_data

    def _on_joined_lobby(self, data):
        logger.info(f"Joined lobby: {data.get('code')}")
        players_data = data.get("players", [])
        if players_data:
            self.current_players = players_data

    def _on_player_joined(self, data):
        players_data = data.get("players", [])
        if players_data:
            self.current_players = players_data
        else:
            self.current_players.append({
                "id": data.get("player_id"),
                "name": data.get("player_name"),
                "is_host": False
            })

    def _on_player_left(self, data):
        player_id = data.get("player_id")
        self.current_players = [p for p in self.current_players if p.get("id") != player_id]

    def _on_player_ready(self, data):
        logger.info(f"Player ready: {data.get('player_id')}")

    def _on_game_started(self, data):
        self.game_state = data.get("game_state", {})
        self.current_player_name = data.get("current_player", "")
        if self.on_game_started:
            self.on_game_started(data)

    def _on_game_state(self, data):
        self.game_state = data.get("game_state", {})
        if self.on_game_state_update:
            self.on_game_state_update(self.game_state)

    def _on_game_state_update(self, data):
        self.game_state = data.get("game_state", {})
        if self.on_game_state_update:
            self.on_game_state_update(self.game_state)

    def _on_lobby_info(self, data):
        self.current_players = data.get("players", [])

    def _on_lobby_update(self, data):
        self.current_players = data.get("players", [])

    def _on_error(self, data):
        logger.error(f"Server error: {data.get('message')}")

    async def host_game(self, player_name: str) -> bool:
        """Host a new game."""
        if not await self.client.connect():
            return False
        success = await self.client.create_lobby(player_name)
        await asyncio.sleep(0.1)
        return success

    async def join_game(self, code: str, player_name: str) -> bool:
        """Join an existing game by code."""
        if not await self.client.connect():
            return False
        success = await self.client.join_lobby(code, player_name)
        await asyncio.sleep(0.1)
        return success

    async def leave_game(self):
        """Leave the current game."""
        if self.client.in_lobby:
            await self.client.leave_lobby()
        await self.client.disconnect()

    async def draw_card(self, player_name: str):
        """Send draw card action to server."""
        await self.client.draw_card(player_name)

    async def play_card(self, player_name: str, card_id: str, target_player: str = None, target_organ: str = None):
        """Send play card action to server."""
        await self.client.play_card(player_name, card_id, target_player, target_organ)

    async def end_turn(self, player_name: str):
        """Send end turn action to server."""
        await self.client.end_turn(player_name)
