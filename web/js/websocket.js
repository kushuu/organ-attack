// WebSocket connection manager
export class WebSocketManager {
    constructor() {
        this.ws = null;
        this.listeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnect = 5;
    }

    connect(url) {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                this.reconnectAttempts = 0;
                this._emit('connected', {});
                resolve();
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this._emit(data.type, data);
                } catch (e) {
                    console.error('Invalid message:', event.data);
                }
            };

            this.ws.onclose = () => {
                this._emit('disconnected', {});
                this._tryReconnect(url);
            };

            this.ws.onerror = (err) => {
                reject(err);
            };
        });
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            return true;
        }
        return false;
    }

    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    _emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }

    _tryReconnect(url) {
        if (this.reconnectAttempts >= this.maxReconnect) return;
        this.reconnectAttempts++;
        setTimeout(() => this.connect(url).catch(() => {}), 2000 * this.reconnectAttempts);
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
