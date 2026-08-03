// Game board rendering
export class GameBoard {
    constructor(app) {
        this.app = app;
        this.state = null;
        this.myName = '';
        this.discardMode = false; // When true, clicking a card discards it

        this.el = {
            turnInfo: document.getElementById('turn-info'),
            phaseInfo: document.getElementById('phase-info'),
            deckCount: document.getElementById('deck-count'),
            discardCount: document.getElementById('discard-count'),
            opponents: document.getElementById('opponents-area'),
            myOrgans: document.getElementById('my-organs'),
            myHand: document.getElementById('my-hand'),
            message: document.getElementById('game-message'),
            drawBtn: document.getElementById('btn-draw'),
            endTurnBtn: document.getElementById('btn-end-turn'),
            discardBtn: document.getElementById('btn-discard'),
            leaveBtn: document.getElementById('btn-leave-game'),
        };

        this.el.drawBtn.addEventListener('click', () => this.app.drawCard());
        this.el.endTurnBtn.addEventListener('click', () => this.app.endTurn());
        this.el.discardBtn.addEventListener('click', () => this.toggleDiscardMode());
        this.el.leaveBtn.addEventListener('click', () => this.app.leaveGame());
    }

    setState(state, myName) {
        this.state = state;
        this.myName = myName;
        this.discardMode = false;
        this.render();
    }

    toggleDiscardMode() {
        this.discardMode = !this.discardMode;
        this.render();
    }

    render() {
        if (!this.state) return;

        const players = this.state.players || [];
        const currentIdx = this.state.current_player_index || 0;
        const currentPlayer = players[currentIdx];
        const isMyTurn = currentPlayer && currentPlayer.name === this.myName;
        const gs = this.state.game_state;
        const phaseText = gs === 1 ? 'PLAY' : gs === 2 ? 'DONE' : 'PLAY';

        // Header info
        this.el.turnInfo.textContent = `Turn: ${currentPlayer ? currentPlayer.name : '--'}`;
        this.el.phaseInfo.textContent = phaseText;
        this.el.phaseInfo.className = `phase-badge ${gs === 1 ? 'play' : 'done'}`;

        const deckLen = this.state.deck_size || 0;
        const discardLen = (this.state.discard_pile || []).length;
        this.el.deckCount.textContent = `Deck: ${deckLen}`;
        this.el.discardCount.textContent = `Discard: ${discardLen}`;

        // Find me
        const myPlayer = players.find(p => p.name === this.myName);
        const cardsPlayed = myPlayer ? myPlayer.cards_played_this_turn : 0;
        const cardsLeft = Math.max(0, 2 - cardsPlayed);

        // Controls
        const canAct = isMyTurn && gs === 1;
        this.el.drawBtn.disabled = !canAct;
        this.el.endTurnBtn.disabled = !canAct;
        this.el.discardBtn.disabled = !canAct;
        this.el.discardBtn.textContent = this.discardMode ? 'Cancel Discard' : 'Discard Card';

        // Opponents
        this.el.opponents.innerHTML = '';
        players.forEach(p => {
            if (p.name === this.myName) return;
            const panel = this._createOpponentPanel(p, p.name === (currentPlayer ? currentPlayer.name : ''));
            this.el.opponents.appendChild(panel);
        });

        // My organs
        if (myPlayer) {
            this.el.myOrgans.innerHTML = '';
            const organs = myPlayer.organs || {};
            Object.entries(organs).forEach(([type, organ]) => {
                this.el.myOrgans.appendChild(this._createOrganChip(organ));
            });

            // My hand
            this.el.myHand.innerHTML = '';

            const handTitle = this.el.myHand.parentElement.querySelector('h3');
            if (handTitle) {
                if (isMyTurn && gs === 1) {
                    handTitle.innerHTML = `My Hand — <span style="color:${cardsLeft > 0 ? 'var(--green)' : 'var(--accent)'}">${cardsLeft} play${cardsLeft !== 1 ? 's' : ''} left</span>`;
                } else {
                    handTitle.textContent = 'My Hand';
                }
            }

            (myPlayer.hand || []).forEach(card => {
                const canPlay = canAct && (cardsPlayed < 2 || this.discardMode);
                const cardEl = this._createCard(card, canPlay);
                this.el.myHand.appendChild(cardEl);
            });
        }
    }

    _createOpponentPanel(player, isCurrentTurn) {
        const panel = document.createElement('div');
        panel.className = `opponent-panel ${player.status === 'eliminated' ? 'eliminated' : ''}`;

        const nameEl = document.createElement('div');
        nameEl.className = 'opponent-name';
        nameEl.textContent = player.name;
        if (player.status === 'eliminated') {
            const tag = document.createElement('span');
            tag.className = 'eliminated-tag';
            tag.textContent = 'ELIMINATED';
            nameEl.appendChild(tag);
        }
        if (isCurrentTurn) {
            nameEl.style.color = 'var(--yellow)';
        }
        panel.appendChild(nameEl);

        const organsGrid = document.createElement('div');
        organsGrid.className = 'opponent-organs';
        Object.entries(player.organs || {}).forEach(([type, organ]) => {
            organsGrid.appendChild(this._createOrganChip(organ));
        });
        panel.appendChild(organsGrid);

        const handInfo = document.createElement('div');
        handInfo.style.cssText = 'margin-top:0.5rem;font-size:0.8rem;color:var(--text-muted)';
        handInfo.textContent = `Cards: ${(player.hand || []).length}`;
        panel.appendChild(handInfo);

        return panel;
    }

    _createOrganChip(organ) {
        const chip = document.createElement('div');
        let statusClass = 'healthy';
        if (organ.is_removed) statusClass = 'removed';
        else if (organ.is_protected) statusClass = 'protected';

        const maxHp = organ.max_hit_points || 1;
        const hp = organ.hit_points ?? maxHp;
        if (!organ.is_removed && maxHp > 1) {
            if (hp <= 1) statusClass = 'critical';
            else if (hp < maxHp) statusClass = 'damaged';
        }

        chip.className = `organ-chip ${statusClass}`;
        if (organ.is_vital) chip.classList.add('vital');

        let protectionLabel = '';
        if (organ.is_protected && organ.protection_source) {
            if (organ.protection_source === 'Vaccination' && organ.protection_expires_at != null) {
                protectionLabel = `<span class="protection-label">Vaccination (expires turn ${organ.protection_expires_at})</span>`;
            } else {
                protectionLabel = `<span class="protection-label">${organ.protection_source}</span>`;
            }
        }

        let hpHtml = '';
        if (maxHp > 1 && !organ.is_removed) {
            const pct = Math.round((hp / maxHp) * 100);
            hpHtml = `<div class="organ-hp"><div class="organ-hp-bar" style="width:${pct}%"></div><span class="organ-hp-text">${hp}/${maxHp}</span></div>`;
        }

        chip.innerHTML = `
            <div>${organ.organ_type || organ.name || '?'}</div>
            ${hpHtml}
            ${protectionLabel}
        `;
        return chip;
    }

    _createCard(card, clickable) {
        const typeClass = (card.type || '').toLowerCase();
        const el = document.createElement('div');
        el.className = `card ${typeClass}`;
        if (!clickable) el.classList.add('disabled');

        // In discard mode, show a different hover style
        if (this.discardMode && clickable) {
            el.style.borderColor = 'var(--yellow)';
        }

        let targetText = '';
        if (card.target) {
            const parts = [];
            if (card.target.organ_type) parts.push(card.target.organ_type);
            if (card.target.player_scope && card.target.player_scope !== 'Other')
                parts.push(card.target.player_scope);
            if (parts.length) targetText = parts.join(' | ');
        }

        el.innerHTML = `
            <div class="card-type-bar">${card.type || 'Unknown'}</div>
            <div class="card-body">
                <div class="card-name">${card.name || '?'}</div>
                <div class="card-desc">${card.description || ''}</div>
                ${targetText ? `<div class="card-target">${targetText}</div>` : ''}
            </div>
        `;

        if (clickable) {
            el.addEventListener('click', () => {
                if (this.discardMode) {
                    this.app.discardCard(card);
                } else {
                    this.app.playCard(card);
                }
            });
        }

        return el;
    }

    showMessage(text, type = 'info') {
        this.el.message.textContent = text;
        this.el.message.className = `game-message ${type}`;
        this.el.message.classList.remove('hidden');
        clearTimeout(this._msgTimeout);
        this._msgTimeout = setTimeout(() => {
            this.el.message.classList.add('hidden');
        }, 3000);
    }
}
