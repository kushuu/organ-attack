"""
Server module for online multiplayer gameplay.
Handles lobby creation, game codes, and real-time player communication.
The server is the authoritative source of game state.
"""

import asyncio
import json
import logging
import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game_engine import GameEngine


def generate_game_code() -> str:
    """Generate a unique 6-character game code."""
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return code


def generate_player_id() -> str:
    """Generate a unique player ID."""
    return str(uuid.uuid4())


@dataclass
class Player:
    """Represents a player in an online game."""
    id: str
    name: str
    websocket: Optional[WebSocketServerProtocol] = None
    is_ready: bool = False
    is_host: bool = False


@dataclass
class GameLobby:
    """Represents a game lobby with players."""
    code: str
    host_id: str
    players: List[Player] = field(default_factory=list)
    max_players: int = 8
    game_started: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    game_engine: Optional[GameEngine] = None

    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    def is_expired(self) -> bool:
        """Check if lobby has expired (30 minutes of inactivity)."""
        return datetime.now() - self.last_activity > timedelta(minutes=30)

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


class LobbyManager:
    """Manages all game lobbies."""

    def __init__(self):
        self.lobbies: Dict[str, GameLobby] = {}
        self.player_lobbies: Dict[str, str] = {}

    def create_lobby(self, host_name: str) -> tuple[GameLobby, Player]:
        """Create a new lobby with the host as the first player."""
        code = generate_game_code()
        while code in self.lobbies:
            code = generate_game_code()

        host_id = generate_player_id()
        host_player = Player(id=host_id, name=host_name, is_host=True)

        lobby = GameLobby(code=code, host_id=host_id)
        lobby.players.append(host_player)

        self.lobbies[code] = lobby
        self.player_lobbies[host_id] = code

        return lobby, host_player

    def join_lobby(self, code: str, player_name: str) -> tuple[Optional[GameLobby], Optional[Player], str]:
        """Join an existing lobby."""
        code = code.upper().strip()

        if code not in self.lobbies:
            return None, None, "Lobby not found"

        lobby = self.lobbies[code]

        if lobby.game_started:
            return None, None, "Game already started"

        if lobby.is_full():
            return None, None, "Lobby is full"

        player_id = generate_player_id()
        player = Player(id=player_id, name=player_name)

        lobby.players.append(player)
        self.player_lobbies[player_id] = code

        return lobby, player, ""

    def leave_lobby(self, player_id: str) -> Optional[GameLobby]:
        """Remove a player from their lobby. Returns the lobby if it still exists."""
        if player_id not in self.player_lobbies:
            return None

        code = self.player_lobbies.pop(player_id)
        lobby = self.lobbies.get(code)

        if not lobby:
            return None

        lobby.players = [p for p in lobby.players if p.id != player_id]

        if not lobby.players:
            del self.lobbies[code]
            return None

        if lobby.host_id == player_id and lobby.players:
            lobby.players[0].is_host = True
            lobby.host_id = lobby.players[0].id

        return lobby

    def get_lobby(self, code: str) -> Optional[GameLobby]:
        """Get a lobby by code."""
        return self.lobbies.get(code.upper())

    def get_lobby_by_player(self, player_id: str) -> Optional[GameLobby]:
        """Get a lobby by player ID."""
        code = self.player_lobbies.get(player_id)
        return self.lobbies.get(code) if code else None

    def set_player_ready(self, player_id: str, ready: bool) -> bool:
        """Set player ready status."""
        lobby = self.get_lobby_by_player(player_id)
        if not lobby:
            return False

        for player in lobby.players:
            if player.id == player_id:
                player.is_ready = ready
                return True
        return False


class GameServer:
    """WebSocket server for handling multiplayer gameplay."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.lobby_manager = LobbyManager()
        self.active_connections: Dict[str, WebSocketServerProtocol] = {}
        self._server = None

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle a new WebSocket connection."""
        player_id = None
        try:
            async for message in websocket:
                try:
                    data = json.loads(message) if isinstance(message, str) else message
                except json.JSONDecodeError:
                    data = {"type": "raw", "data": str(message)}

                if not isinstance(data, dict):
                    data = {"type": "raw", "data": str(data)}

                msg_type = data.get("type", "unknown")
                logger.debug(f"Received: {msg_type}")

                if msg_type == "create_lobby":
                    player_id = await self._handle_create_lobby(websocket, data)
                elif msg_type == "join_lobby":
                    player_id = await self._handle_join_lobby(websocket, data)
                elif msg_type == "leave_lobby":
                    await self._handle_leave_lobby(websocket, data, player_id)
                elif msg_type == "player_ready":
                    await self._handle_player_ready(websocket, data, player_id)
                elif msg_type == "start_game":
                    await self._handle_start_game(websocket, data, player_id)
                elif msg_type == "game_action":
                    await self._handle_game_action(websocket, data, player_id)
                elif msg_type == "get_game_state":
                    await self._handle_get_game_state(websocket, data, player_id)
                elif msg_type == "get_lobby_info":
                    await self._handle_get_lobby_info(websocket, data, player_id)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed")
        finally:
            if player_id:
                lobby = self.lobby_manager.get_lobby_by_player(player_id)
                lobby_code = lobby.code if lobby else None
                self.lobby_manager.leave_lobby(player_id)
                self.active_connections.pop(player_id, None)
                if lobby_code:
                    await self._broadcast_lobby_update(lobby_code)

    async def _handle_create_lobby(self, websocket: WebSocketServerProtocol, data: dict) -> str:
        """Handle lobby creation."""
        player_name = data.get("player_name", "Host")
        lobby, player = self.lobby_manager.create_lobby(player_name)

        player.websocket = websocket
        self.active_connections[player.id] = websocket

        await self._send(websocket, {
            "type": "lobby_created",
            "code": lobby.code,
            "player_id": player.id,
            "is_host": True,
            "players": [{"id": p.id, "name": p.name, "is_host": p.is_host} for p in lobby.players]
        })

        return player.id

    async def _handle_join_lobby(self, websocket: WebSocketServerProtocol, data: dict) -> str:
        """Handle joining a lobby."""
        code = data.get("code", "").upper()
        player_name = data.get("player_name", "Player")

        lobby, player, error = self.lobby_manager.join_lobby(code, player_name)

        if error:
            await self._send(websocket, {"type": "error", "message": error})
            return None

        player.websocket = websocket
        self.active_connections[player.id] = websocket

        await self._send(websocket, {
            "type": "joined_lobby",
            "code": lobby.code,
            "player_id": player.id,
            "is_host": False,
            "players": [{"id": p.id, "name": p.name, "is_host": p.is_host} for p in lobby.players]
        })

        await self._broadcast_to_lobby(lobby.code, {
            "type": "player_joined",
            "player_name": player.name,
            "player_id": player.id,
            "players": [{"id": p.id, "name": p.name, "is_host": p.is_host} for p in lobby.players]
        }, exclude_id=player.id)

        return player.id

    async def _handle_leave_lobby(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Handle leaving a lobby."""
        if not player_id:
            return

        lobby = self.lobby_manager.leave_lobby(player_id)
        if lobby:
            await self._broadcast_to_lobby(lobby.code, {
                "type": "player_left",
                "player_id": player_id,
                "players": [{"id": p.id, "name": p.name, "is_host": p.is_host} for p in lobby.players]
            })

    async def _handle_player_ready(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Handle player ready status."""
        if not player_id:
            return

        ready = data.get("ready", False)
        self.lobby_manager.set_player_ready(player_id, ready)

        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        if lobby:
            lobby.touch()
            await self._broadcast_to_lobby(lobby.code, {
                "type": "player_ready",
                "player_id": player_id,
                "ready": ready
            })

    async def _handle_start_game(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Handle game start. Only host can start."""
        if not player_id:
            return

        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        if not lobby or lobby.host_id != player_id:
            await self._send(websocket, {"type": "error", "message": "Only the host can start the game"})
            return

        if len(lobby.players) < 2:
            await self._send(websocket, {"type": "error", "message": "Need at least 2 players to start"})
            return

        player_names = [p.name for p in lobby.players]
        lobby.game_engine = GameEngine(player_names)
        lobby.game_started = True
        lobby.touch()

        game_state = lobby.game_engine.to_dict()

        await self._broadcast_to_lobby(lobby.code, {
            "type": "game_started",
            "game_state": game_state,
            "current_player": lobby.game_engine.get_current_player().name
        })

    async def _handle_game_action(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Handle in-game actions. Server is authoritative — processes action on its engine."""
        if not player_id:
            return

        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        if not lobby or not lobby.game_engine:
            await self._send(websocket, {"type": "error", "message": "Game not started"})
            return

        action = data.get("action")
        action_data = data.get("data", {})
        engine = lobby.game_engine
        lobby.touch()

        # Find the player by name in the engine (server maps player_id -> engine player)
        requesting_engine_player = None
        for p in engine.players:
            if p.name == action_data.get("player_name"):
                requesting_engine_player = p
                break

        if not requesting_engine_player:
            await self._send(websocket, {"type": "error", "message": "Player not found in game"})
            return

        result = None

        try:
            if action == "draw_card":
                result = self._process_draw_card(engine, requesting_engine_player)
            elif action == "play_card":
                result = self._process_play_card(engine, requesting_engine_player, action_data)
            elif action == "discard_card":
                result = self._process_discard_card(engine, requesting_engine_player, action_data)
            elif action == "end_turn":
                result = self._process_end_turn(engine)
            elif action == "block_attack":
                result = self._process_block_attack(engine, requesting_engine_player, action_data)
            else:
                await self._send(websocket, {"type": "error", "message": f"Unknown action: {action}"})
                return
        except Exception as e:
            logger.error(f"Error processing action '{action}': {e}", exc_info=True)
            result = {"success": False, "error": str(e)}

        # Always broadcast updated state, even if processing failed
        try:
            game_state = engine.to_dict()
            await self._broadcast_to_lobby(lobby.code, {
                "type": "game_state_update",
                "game_state": game_state,
                "action": action,
                "action_data": action_data,
                "result": result
            })
        except Exception as e:
            logger.error(f"Error broadcasting state: {e}", exc_info=True)
            await self._send(websocket, {
                "type": "error",
                "message": f"Failed to update game state: {e}"
            })

    def _process_draw_card(self, engine: GameEngine, player) -> dict:
        """Process a draw card action on the server engine."""
        if engine.game_state.value != 1:  # GameState.PLAY
            return {"success": False, "error": "Not in play phase"}

        card = engine.draw_card_for_player(player)
        if card:
            return {"success": True, "card_drawn": card.name}
        return {"success": False, "error": "No cards to draw"}

    def _process_play_card(self, engine: GameEngine, player, action_data: dict) -> dict:
        """Process a play card action on the server engine. Max 2 cards per turn."""
        if engine.game_state.value != 1:  # GameState.PLAY
            return {"success": False, "error": "Not in play phase"}

        if player.cards_played_this_turn >= 2:
            return {"success": False, "error": "Already played 2 cards this turn"}

        card_id = action_data.get("card_id")
        target_player_name = action_data.get("target_player")
        target_organ = action_data.get("target_organ")

        # Find the card in the player's hand
        card = None
        for c in player.hand:
            if c.id == card_id:
                card = c
                break

        if not card:
            return {"success": False, "error": "Card not in hand"}

        # Validate card conditions
        valid, reason = engine.card_manager.validate_card_play(card, player, engine)
        if not valid:
            return {"success": False, "error": reason}

        # Find target player in engine
        target_engine_player = None
        if target_player_name:
            for p in engine.players:
                if p.name == target_player_name:
                    target_engine_player = p
                    break

        # Validate target_organ_must_be_present condition
        if card.conditions and card.conditions.target_organ_must_be_present:
            if target_engine_player and target_organ:
                if not target_engine_player.has_organ(target_organ):
                    return {"success": False, "error": f"{target_engine_player.name} does not have {target_organ}"}

        # Validate target organ is not protected for attacks
        if target_engine_player and target_organ:
            if card.conditions and not card.conditions.organ_must_not_be_protected:
                pass  # Protection is checked in the effect processor
            if card.conditions and card.conditions.organ_must_not_be_protected:
                if target_engine_player.is_organ_protected(target_organ):
                    return {"success": False, "error": f"{target_organ} is protected"}

        # Remove card from hand
        player.remove_card_from_hand(card)

        # Process card effects
        results = engine.effect_processor.process_card_effects(
            card, player, target_engine_player, target_organ
        )

        # Add card to discard pile
        engine.discard_pile.append(card)

        player.cards_played_this_turn += 1

        return {
            "success": True,
            "card_played": card.name,
            "cards_remaining": 2 - player.cards_played_this_turn,
            "effects": results
        }

    def _process_discard_card(self, engine: GameEngine, player, action_data: dict) -> dict:
        """Process discarding a card without playing it. Counts toward the 2-card limit."""
        if engine.game_state.value != 1:  # GameState.PLAY
            return {"success": False, "error": "Not in play phase"}

        if player.cards_played_this_turn >= 2:
            return {"success": False, "error": "Already played 2 cards this turn"}

        card_id = action_data.get("card_id")

        # Find the card in the player's hand
        card = None
        for c in player.hand:
            if c.id == card_id:
                card = c
                break

        if not card:
            return {"success": False, "error": "Card not in hand"}

        # Remove from hand and add to discard
        player.remove_card_from_hand(card)
        engine.discard_pile.append(card)
        player.cards_played_this_turn += 1

        return {
            "success": True,
            "card_discarded": card.name,
            "cards_remaining": 2 - player.cards_played_this_turn
        }

    def _process_block_attack(self, engine: GameEngine, player, action_data: dict) -> dict:
        """Process a block attack action."""
        if engine.current_attack:
            engine.current_attack['blocked'] = True
            engine.current_attack['blocked_by'] = player.name
            return {"success": True, "blocked_by": player.name}
        return {"success": False, "error": "No attack to block"}

    def _process_end_turn(self, engine: GameEngine) -> dict:
        """Process end turn on the server engine."""
        # Remove non-permanent protections and expired Vaccination protections
        for player in engine.players:
            for organ in player.organs.values():
                if organ.is_protected:
                    # Strip non-Vaccination protections immediately
                    if organ.protection_source and organ.protection_source != 'Vaccination':
                        organ.is_protected = False
                        organ.protection_source = None
                        organ.protection_expires_at = None
                    # Strip Vaccination protection if it has expired
                    elif organ.protection_source == 'Vaccination' and organ.protection_expires_at is not None:
                        if engine.turn_count >= organ.protection_expires_at:
                            organ.is_protected = False
                            organ.protection_source = None
                            organ.protection_expires_at = None

        # Check if current player has an extra turn (Caffeine Rush)
        current_player = engine.get_current_player()
        if current_player.can_draw_extra:
            # Grant extra turn: replenish hand, reset counters, stay on same player
            current_player.can_draw_extra = False
            while len(current_player.hand) < 5:
                card = engine.draw_card_for_player(current_player)
                if not card:
                    break
            current_player.reset_turn_counters()
            engine.turn_count += 1
            return {
                "success": True,
                "game_over": False,
                "extra_turn": True,
                "current_player": current_player.name,
                "hand_size": len(current_player.hand)
            }

        # Check for game end
        active_players = engine.get_active_players()
        if len(active_players) <= 1:
            engine.game_state = engine.game_state.DONE
            winner = active_players[0] if active_players else None
            return {
                "success": True,
                "game_over": True,
                "winner": winner.name if winner else None
            }

        # Advance to next non-eliminated player, skipping those with skip_next_turn
        num_players = len(engine.players)
        for _ in range(num_players):
            engine.current_player_index = (engine.current_player_index + 1) % num_players
            next_player = engine.get_current_player()
            if next_player.is_eliminated():
                continue
            if next_player.skip_next_turn:
                next_player.skip_next_turn = False
                continue
            break

        # Replenish hand to 5 cards for the new current player
        current_player = engine.get_current_player()
        cards_drawn = 0
        while len(current_player.hand) < 5:
            card = engine.draw_card_for_player(current_player)
            if not card:
                break
            cards_drawn += 1

        # Reset turn counters
        current_player.reset_turn_counters()

        engine.game_state = engine.game_state.PLAY
        engine.turn_count += 1

        return {
            "success": True,
            "game_over": False,
            "current_player": current_player.name,
            "cards_drawn": cards_drawn,
            "hand_size": len(current_player.hand)
        }

    async def _handle_get_game_state(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Get current game state."""
        if not player_id:
            return

        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        if not lobby or not lobby.game_engine:
            await self._send(websocket, {"type": "error", "message": "Game not started"})
            return

        await self._send(websocket, {
            "type": "game_state",
            "game_state": lobby.game_engine.to_dict()
        })

    async def _handle_get_lobby_info(self, websocket: WebSocketServerProtocol, data: dict, player_id: str):
        """Get current lobby information."""
        if not player_id:
            return

        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        if not lobby:
            await self._send(websocket, {"type": "error", "message": "Not in a lobby"})
            return

        await self._send(websocket, {
            "type": "lobby_info",
            "code": lobby.code,
            "players": [
                {"id": p.id, "name": p.name, "is_ready": p.is_ready, "is_host": p.is_host}
                for p in lobby.players
            ],
            "game_started": lobby.game_started
        })

    async def _broadcast_to_lobby(self, code: str, message: dict, exclude_id: str = None):
        """Broadcast message to all players in a lobby."""
        lobby = self.lobby_manager.get_lobby(code)
        if not lobby:
            return

        for player in lobby.players:
            if player.id != exclude_id and player.websocket:
                try:
                    await self._send(player.websocket, message)
                except Exception as e:
                    logger.error(f"Error sending to {player.name}: {e}")

    async def _broadcast_lobby_update(self, lobby_code: str):
        """Broadcast lobby update to all players in lobby."""
        lobby = self.lobby_manager.get_lobby(lobby_code)
        if lobby:
            await self._broadcast_to_lobby(lobby.code, {
                "type": "lobby_update",
                "players": [
                    {"id": p.id, "name": p.name, "is_ready": p.is_ready, "is_host": p.is_host}
                    for p in lobby.players
                ]
            })

    async def _send(self, websocket: WebSocketServerProtocol, message: dict):
        """Send a message to a WebSocket."""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def start(self):
        """Start the WebSocket server."""
        self._server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )

    async def stop(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()


async def start_server(host: str = "0.0.0.0", port: int = 8765):
    """Start the game server."""
    server = GameServer(host, port)
    await server.start()
    return server


async def run_server(host: str = "0.0.0.0", port: int = 8765):
    """Run the server (blocking)."""
    server = await start_server(host, port)
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        await server.stop()
