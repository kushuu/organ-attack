// Lobby UI management
export class Lobby {
    constructor(app) {
        this.app = app;
        this.isHost = false;
        this.players = [];

        this.el = {
            code: document.getElementById('lobby-code'),
            playerList: document.getElementById('player-list'),
            startBtn: document.getElementById('btn-start-game'),
            leaveBtn: document.getElementById('btn-leave-lobby'),
            copyBtn: document.getElementById('btn-copy-code'),
        };

        this.el.startBtn.addEventListener('click', () => this.app.startGame());
        this.el.leaveBtn.addEventListener('click', () => this.app.leaveLobby());
        this.el.copyBtn.addEventListener('click', () => this.copyCode());
    }

    show(code, players, isHost) {
        this.isHost = isHost;
        this.players = players;
        this.el.code.textContent = code;
        this.el.startBtn.classList.toggle('hidden', !isHost);
        this.renderPlayers();
    }

    updatePlayers(players) {
        this.players = players;
        this.renderPlayers();
    }

    renderPlayers() {
        this.el.playerList.innerHTML = '';
        this.players.forEach(p => {
            const li = document.createElement('li');
            li.textContent = p.name || 'Unknown';
            if (p.is_host) {
                const badge = document.createElement('span');
                badge.className = 'host-badge';
                badge.textContent = 'HOST';
                li.appendChild(badge);
            }
            this.el.playerList.appendChild(li);
        });
    }

    copyCode() {
        const code = this.el.code.textContent;
        navigator.clipboard.writeText(code).then(() => {
            this.app.toast('Code copied!');
        });
    }
}
