// Main application controller
import { WebSocketManager } from './websocket.js';
import { Lobby } from './lobby.js';
import { GameBoard } from './game.js';
import { TargetSelector } from './target.js';

class App {
    constructor() {
        this.ws = new WebSocketManager();
        this.lobby = new Lobby(this);
        this.gameBoard = new GameBoard(this);
        this.targetSelector = new TargetSelector();

        this.myName = '';
        this.myPlayerId = null;
        this.isHost = false;
        this.engine = null; // local copy of game state for target selection

        this.views = {
            home: document.getElementById('view-home'),
            lobby: document.getElementById('view-lobby'),
            game: document.getElementById('view-game'),
        };

        this._setupHomeEvents();
        this._setupWebSocketEvents();
        this._setupGameEvents();
    }

    // ---- View Management ----
    showView(name) {
        Object.values(this.views).forEach(v => v.classList.remove('active'));
        this.views[name].classList.add('active');
    }

    // ---- Home ----
    _setupHomeEvents() {
        document.getElementById('btn-host').addEventListener('click', () => this.hostGame());
        document.getElementById('btn-join-show').addEventListener('click', () => {
            document.getElementById('join-form').classList.remove('hidden');
        });
        document.getElementById('btn-join').addEventListener('click', () => this.joinGame());
    }

    async hostGame() {
        const name = document.getElementById('player-name').value.trim();
        const url = document.getElementById('server-url').value.trim();
        if (!name) return this.setHomeStatus('Enter your name');
        if (!url) return this.setHomeStatus('Enter server address');

        this.myName = name;
        try {
            await this.ws.connect(url);
            this.ws.send({ type: 'create_lobby', player_name: name });
        } catch (e) {
            this.setHomeStatus('Cannot connect to server');
        }
    }

    async joinGame() {
        const name = document.getElementById('player-name').value.trim();
        const url = document.getElementById('server-url').value.trim();
        const code = document.getElementById('game-code').value.trim().toUpperCase();
        if (!name) return this.setHomeStatus('Enter your name');
        if (!url) return this.setHomeStatus('Enter server address');
        if (!code || code.length !== 6) return this.setHomeStatus('Enter 6-character code');

        this.myName = name;
        try {
            await this.ws.connect(url);
            this.ws.send({ type: 'join_lobby', code, player_name: name });
        } catch (e) {
            this.setHomeStatus('Cannot connect to server');
        }
    }

    setHomeStatus(msg) {
        document.getElementById('home-status').textContent = msg;
    }

    // ---- WebSocket Events ----
    _setupWebSocketEvents() {
        this.ws.on('lobby_created', (data) => {
            this.myPlayerId = data.player_id;
            this.isHost = true;
            this.lobby.show(data.code, data.players || [], true);
            this.showView('lobby');
        });

        this.ws.on('joined_lobby', (data) => {
            this.myPlayerId = data.player_id;
            this.isHost = false;
            this.lobby.show(data.code, data.players || [], false);
            this.showView('lobby');
        });

        this.ws.on('player_joined', (data) => {
            this.lobby.updatePlayers(data.players || []);
        });

        this.ws.on('player_left', (data) => {
            this.lobby.updatePlayers(data.players || []);
        });

        this.ws.on('lobby_update', (data) => {
            this.lobby.updatePlayers(data.players || []);
        });

        this.ws.on('game_started', (data) => {
            this._handleGameState(data.game_state);
            this.showView('game');
        });

        this.ws.on('game_state_update', (data) => {
            this._handleGameState(data.game_state);
            if (data.result) {
                const msg = data.result.success ?
                    (data.result.card_played ? `Played ${data.result.card_played}` : 'Action completed') :
                    (data.result.error || 'Action failed');
                this.gameBoard.showMessage(msg, data.result.success ? 'success' : 'error');
            }
        });

        this.ws.on('game_state', (data) => {
            this._handleGameState(data.game_state);
        });

        this.ws.on('error', (data) => {
            this.setHomeStatus(data.message || 'Error');
            this.gameBoard.showMessage(data.message || 'Error', 'error');
        });

        this.ws.on('disconnected', () => {
            this.gameBoard.showMessage('Disconnected from server', 'error');
        });
    }

    _handleGameState(gameState) {
        if (!gameState) return;
        this.engine = gameState;
        this.gameBoard.setState(gameState, this.myName);

        // Check for game over
        if (gameState.game_state === 2) { // GameState.DONE = 2
            this._showGameOver(gameState);
        }
    }

    _showGameOver(gameState) {
        const players = gameState.players || [];
        const myPlayer = players.find(p => p.name === this.myName);

        // Determine if I won
        const activePlayers = players.filter(p => p.status !== 'eliminated');
        const winner = activePlayers.length === 1 ? activePlayers[0] : null;
        const iWon = winner && winner.name === this.myName;

        // Witty messages
        const winMessages = [
            "Your organs are still standing!",
            "The last organ standing wins!",
            "Your body is a temple — and it's indestructible!",
            "Medical science is baffled!",
            "You survived the organ harvest!",
            "Your immune system is LEGENDARY!",
            "The doctor will see you now... as the champion!",
            "Other players' organs? Never heard of them.",
            "You didn't just win — you dominated!",
            "Your organs called. They said 'we're not going anywhere!'"
        ];

        const loseMessages = [
            "Your organs have left the chat.",
            "Better luck next time, organ donor!",
            "Your body couldn't take it anymore.",
            "The hospital called — they want their organs back.",
            "At least you still have your... personality?",
            "Don't worry, you can always donate a new set!",
            "Your organs went on vacation. Permanently.",
            "Looks like you're going to need a transplant!",
            "Your body is now a vacant lot.",
            "Don't feel bad — even organs have a breaking point!"
        ];

        const title = iWon ? "VICTORY!" : "GAME OVER";
        const message = iWon
            ? `${winner.name} is the champion!`
            : winner
                ? `${winner.name} wins!`
                : "Game Over!";
        const subtitle = iWon
            ? winMessages[Math.floor(Math.random() * winMessages.length)]
            : loseMessages[Math.floor(Math.random() * loseMessages.length)];

        document.getElementById('game-over-title').textContent = title;
        document.getElementById('game-over-message').textContent = message;
        document.getElementById('game-over-subtitle').textContent = subtitle;

        const modal = document.getElementById('game-over-modal');
        modal.classList.remove('hidden');

        // Spawn confetti
        this._spawnConfetti();

        // Play again button
        document.getElementById('btn-play-again').onclick = () => {
            modal.classList.add('hidden');
            this.leaveGame();
        };
    }

    _spawnConfetti() {
        const container = document.getElementById('confetti-container');
        container.innerHTML = '';
        const colors = ['#e74c3c', '#2ecc71', '#3498db', '#f39c12', '#9b59b6', '#e67e22', '#1abc9c'];
        const shapes = ['square', 'circle'];

        for (let i = 0; i < 80; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            const color = colors[Math.floor(Math.random() * colors.length)];
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            const size = Math.random() * 8 + 6;
            const left = Math.random() * 100;
            const delay = Math.random() * 2;
            const duration = Math.random() * 2 + 2;

            confetti.style.left = `${left}%`;
            confetti.style.width = `${size}px`;
            confetti.style.height = `${size}px`;
            confetti.style.backgroundColor = color;
            confetti.style.borderRadius = shape === 'circle' ? '50%' : '2px';
            confetti.style.animationDuration = `${duration}s`;
            confetti.style.animationDelay = `${delay}s`;

            container.appendChild(confetti);
        }

        // Clean up after animation
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    }

    // ---- Game Actions ----
    _setupGameEvents() {
        document.getElementById('btn-leave-game').addEventListener('click', () => this.leaveGame());
    }

    drawCard() {
        this.ws.send({
            type: 'game_action',
            action: 'draw_card',
            data: { player_name: this.myName }
        });
    }

    endTurn() {
        this.gameBoard.discardMode = false;
        this.ws.send({
            type: 'game_action',
            action: 'end_turn',
            data: { player_name: this.myName }
        });
    }

    discardCard(card) {
        this.ws.send({
            type: 'game_action',
            action: 'discard_card',
            data: {
                player_name: this.myName,
                card_id: card.id
            }
        });
        this.gameBoard.discardMode = false;
    }

    async playCard(card) {
        if (!this.engine) return;

        // If card has a target, show target selector
        if (card.target) {
            const result = await this.targetSelector.show(card, this.engine, this.myName);
            if (!result) return; // cancelled

            if (result.action === 'discard') {
                // User chose to discard from the modal
                this.discardCard(result.card);
                return;
            }

            // result.action === 'play'
            const targetName = result.player ? result.player.name : null;
            const targetOrgan = result.organ || null;

            this.ws.send({
                type: 'game_action',
                action: 'play_card',
                data: {
                    player_name: this.myName,
                    card_id: card.id,
                    target_player: targetName,
                    target_organ: targetOrgan
                }
            });
        } else {
            this.ws.send({
                type: 'game_action',
                action: 'play_card',
                data: {
                    player_name: this.myName,
                    card_id: card.id
                }
            });
        }
    }

    startGame() {
        this.ws.send({ type: 'start_game' });
    }

    leaveLobby() {
        this.ws.send({ type: 'leave_lobby' });
        this.ws.disconnect();
        this.showView('home');
    }

    leaveGame() {
        this.ws.send({ type: 'leave_lobby' });
        this.ws.disconnect();
        this.showView('home');
    }

    toast(msg) {
        const el = document.getElementById('toast');
        el.textContent = msg;
        el.classList.remove('hidden');
        clearTimeout(this._toastTimeout);
        this._toastTimeout = setTimeout(() => el.classList.add('hidden'), 2000);
    }
}

// Start
const app = new App();
