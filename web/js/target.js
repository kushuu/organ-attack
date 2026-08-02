// Target selection modal
export class TargetSelector {
    constructor() {
        this.modal = document.getElementById('target-modal');
        this.title = document.getElementById('modal-title');
        this.desc = document.getElementById('modal-desc');
        this.playersDiv = document.getElementById('modal-players');
        this.organsDiv = document.getElementById('modal-organs');
        this.organList = document.getElementById('modal-organ-list');
        this.okBtn = document.getElementById('modal-ok');
        this.cancelBtn = document.getElementById('modal-cancel');
        this.discardBtn = document.getElementById('modal-discard');

        this.selectedPlayer = null;
        this.selectedOrgan = null;
        this.resolve = null;

        this.okBtn.addEventListener('click', () => this._confirm());
        this.cancelBtn.addEventListener('click', () => this._cancel());
        this.discardBtn.addEventListener('click', () => this._discard());
    }

    show(card, engine, myName) {
        return new Promise((resolve) => {
            this.resolve = resolve;
            this.currentCard = card;
            this.selectedPlayer = null;
            this.selectedOrgan = null;
            this.okBtn.disabled = true;

            // Show discard option for cards with targets
            if (card.target) {
                this.discardBtn.classList.remove('hidden');
            } else {
                this.discardBtn.classList.add('hidden');
            }

            if (!card.target) {
                this._confirm();
                return;
            }

            const target = card.target;
            const typeEmoji = {
                'Attack': '⚔️',
                'Defense': '🛡️',
                'Action': '✨',
                'Wildcard': '🃏'
            }[card.type] || '';

            let organInfo = '';
            if (target.organ_type && target.organ_type !== 'Any') {
                organInfo = ` → ${target.organ_type}`;
                this.selectedOrgan = target.organ_type;
            } else if (target.organ_type === 'Any') {
                organInfo = ' → Choose an organ';
            }

            this.title.textContent = `${typeEmoji} ${card.name}${organInfo}`;
            this.desc.textContent = card.description || `Select a target player`;

            // Player selection
            this.playersDiv.innerHTML = '';
            this.organsDiv.classList.add('hidden');

            let players = [];
            if (target.player_scope === 'Other') {
                players = (engine.players || []).filter(p => p.name !== myName && p.status !== 'eliminated');
            } else if (target.player_scope === 'Any') {
                players = (engine.players || []).filter(p => p.status !== 'eliminated');
            } else if (target.player_scope === 'Self') {
                players = (engine.players || []).filter(p => p.name === myName);
            } else if (target.player_scope === 'All') {
                this.selectedPlayer = null;
                this.selectedOrgan = target.organ_type !== 'Any' ? target.organ_type : null;
                if (target.organ_type && target.organ_type !== 'Any') {
                    this._confirm();
                    return;
                }
                this._show();
                return;
            }

            if (players.length === 0) {
                this.desc.textContent = 'No valid targets available. You can discard this card instead.';
                this.okBtn.disabled = true;
                this._show();
                return;
            }

            players.forEach(p => {
                const btn = document.createElement('button');
                btn.className = 'modal-player-btn';
                const organs = Object.values(p.organs || {}).filter(o => !o.is_removed);

                let organHint = '';
                if (target.organ_type && target.organ_type !== 'Any') {
                    const targetOrgan = organs.find(o => o.organ_type === target.organ_type);
                    if (!targetOrgan) {
                        organHint = ` — <span style="color:var(--accent)">No ${target.organ_type}!</span>`;
                    } else if (targetOrgan.is_protected) {
                        organHint = ` — <span style="color:var(--blue)">${target.organ_type} is protected</span>`;
                    } else {
                        organHint = ` — <span style="color:var(--green)">${target.organ_type} is exposed</span>`;
                    }
                }

                btn.innerHTML = `<strong>${p.name}</strong> (${organs.length} organs)${organHint}`;
                btn.addEventListener('click', () => {
                    this.playersDiv.querySelectorAll('.modal-player-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    this.selectedPlayer = p;
                    this.okBtn.disabled = false;

                    if (target.organ_type === 'Any') {
                        this._updateOrgans(p);
                    }
                });
                this.playersDiv.appendChild(btn);
            });

            // Auto-select if only one valid target
            if (players.length === 1) {
                const btn = this.playersDiv.querySelector('.modal-player-btn');
                if (btn) btn.click();
            }

            this._show();
        });
    }

    _updateOrgans(player) {
        const organs = Object.values(player.organs || {}).filter(o => !o.is_removed);
        if (organs.length === 0) return;

        this.organsDiv.classList.remove('hidden');
        this.organList.innerHTML = '';

        organs.forEach(organ => {
            const chip = document.createElement('div');
            chip.className = 'organ-chip';
            if (organ.is_protected) chip.classList.add('protected');
            else chip.classList.add('healthy');
            if (organ.is_vital) chip.classList.add('vital');

            chip.innerHTML = `<div>${organ.organ_type}</div>`;
            chip.addEventListener('click', () => {
                this.organList.querySelectorAll('.organ-chip').forEach(c => c.classList.remove('selected'));
                chip.classList.add('selected');
                this.selectedOrgan = organ.organ_type;
            });
            this.organList.appendChild(chip);
        });

        this.organList.querySelector('.organ-chip')?.click();
    }

    _show() {
        this.modal.classList.remove('hidden');
    }

    _confirm() {
        this.modal.classList.add('hidden');
        if (this.resolve) {
            this.resolve({
                action: 'play',
                player: this.selectedPlayer,
                organ: this.selectedOrgan
            });
        }
    }

    _cancel() {
        this.modal.classList.add('hidden');
        if (this.resolve) {
            this.resolve(null);
        }
    }

    _discard() {
        this.modal.classList.add('hidden');
        if (this.resolve) {
            this.resolve({
                action: 'discard',
                card: this.currentCard
            });
        }
    }
}
