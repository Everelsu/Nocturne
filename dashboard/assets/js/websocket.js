class Socket {
    constructor(player, url) {
        this.player = player;
        this.url = url;
        this.socket = null;
        this.heartbeatInterval = null;
        this.heartbeatMessage = { op: "heartbeat" };
        this.DISCONNECT_DELAY = 30000; // Delay before disconnecting (in milliseconds)
        this.RECONNECT_BASE_DELAY = 2000; // Initial delay for reconnect attempts (2 seconds)
        this.RECONNECT_MAX_DELAY = 30000; // Maximum delay for reconnect attempts (30 seconds)
        this.reconnectAttempts = 0; // Track the number of reconnect attempts
        this.disconnectTimeout = null;

        // Binding methods
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        this.initVisibilityListener();
    }

    // Initialize the socket connection
    connect() {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log("Connected to server!");
            updateWarningBar(false); // Custom function to update UI (assumed to exist)
            this.startHeartbeat();
            if (this.callback) this.addMessageListener(this.callback);
            this.reconnectAttempts = 0; // Reset reconnect attempts on successful connection
        };

        this.socket.onclose = () => {
            console.log("Disconnected from server!");
            updateWarningBar(true); // Custom function to update UI (assumed to exist)
            this.player.init();
            this.player.selectedBot = null;
            this.stopHeartbeat();
            this.scheduleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket error: ", error);
            this.scheduleReconnect();
        };
    }

    // Schedule a reconnect with a delay (exponential backoff with a cap)
    scheduleReconnect() {
        if (document.visibilityState === "visible") {
            const delay = Math.min(
                this.RECONNECT_BASE_DELAY * Math.pow(2, this.reconnectAttempts),
                this.RECONNECT_MAX_DELAY
            );
            this.reconnectAttempts += 1;
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(() => this.reconnect(), delay);
        }
    }

    // Attempt to reconnect if the socket is closed
    reconnect() {
        if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
            console.log("Attempting to reconnect...");
            this.connect();
        }
    }

    // Disconnect the socket
    disconnect() {
        if (this.socket) {
            console.log("Disconnecting WebSocket...");
            this.stopHeartbeat();
            this.socket.close();
            this.socket = null;
        }
    }

    // Send a message via WebSocket
    send(msg) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(msg));
        }
    }

    // Start sending heartbeat messages at regular intervals
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.send(this.heartbeatMessage);
        }, 60000); // Send heartbeat every 60 seconds
    }

    // Stop sending heartbeat messages
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    // Handle tab visibility changes
    handleVisibilityChange() {
        if (document.visibilityState === "hidden") {
            this.disconnectTimeout = setTimeout(() => {
                this.disconnect();
            }, this.DISCONNECT_DELAY);
        } else if (document.visibilityState === "visible") {
            clearTimeout(this.disconnectTimeout); // Cancel disconnect if user returns
            this.reconnect();
        }
    }

    // Add a message listener to handle incoming WebSocket messages
    addMessageListener(callback) {
        this.callback = callback; // Store the callback for later use
        if (this.socket) {
            this.socket.onmessage = (event) => {
                callback(event.data);
            };
        }
    }

    // Remove the message listener
    removeMessageListener() {
        if (this.socket) {
            this.socket.onmessage = null;
        }
    }

    // Initialize the visibility change listener
    initVisibilityListener() {
        document.addEventListener(
            "visibilitychange",
            this.handleVisibilityChange
        );
    }

    // Clean up the visibility change listener
    cleanupVisibilityListener() {
        document.removeEventListener(
            "visibilitychange",
            this.handleVisibilityChange
        );
    }

    // Clean up the socket and related resources
    cleanup() {
        this.disconnect();
        this.cleanupVisibilityListener();
        clearTimeout(this.disconnectTimeout);
        this.stopHeartbeat();
    }
}
