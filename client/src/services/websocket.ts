/**
 * WebSocket Service for real-time execution updates
 *
 * Uses native WebSocket connection to FastAPI backend.
 * Replaces Azure Web PubSub with simpler native implementation.
 *
 * Provides connection management and event subscriptions for:
 * - Execution status updates (for execution details screen)
 * - Execution log messages
 * - User notifications
 */

export interface ExecutionUpdate {
	executionId: string;
	status: string;
	isComplete: boolean;
	timestamp: string;
	result?: unknown;
	error?: string;
	duration_ms?: number;
}

export interface ExecutionLog {
	executionId: string;
	timestamp: string;
	level: string;
	message: string;
	sequence?: number;
	data?: Record<string, unknown>;
}

export interface NewExecution {
	execution_id: string;
	workflow_name: string;
	executed_by: string;
	executed_by_name: string;
	status: string;
	started_at: string;
	timestamp: string;
}

export interface HistoryUpdate {
	execution_id: string;
	workflow_name: string;
	status: string;
	executed_by: string;
	executed_by_name: string;
	started_at: string;
	completed_at?: string;
	duration_ms?: number;
	timestamp: string;
}

export interface PackageLog {
	level: string;
	message: string;
}

export interface PackageComplete {
	status: "success" | "error";
	message: string;
}

// Message types from backend
type WebSocketMessage =
	| { type: "connected"; channels: string[]; userId: string }
	| { type: "connected"; executionId: string }
	| { type: "subscribed"; channel: string }
	| { type: "unsubscribed"; channel: string }
	| { type: "pong" }
	| { type: "execution_update"; executionId: string; [key: string]: unknown }
	| { type: "execution_log"; executionId: string; [key: string]: unknown }
	| { type: "notification"; [key: string]: unknown }
	| { type: "log"; level: string; message: string }
	| { type: "complete"; status: "success" | "error"; message: string };

type ExecutionUpdateCallback = (update: ExecutionUpdate) => void;
type ExecutionLogCallback = (log: ExecutionLog) => void;
type NewExecutionCallback = (execution: NewExecution) => void;
type HistoryUpdateCallback = (update: HistoryUpdate) => void;
type PackageLogCallback = (log: PackageLog) => void;
type PackageCompleteCallback = (complete: PackageComplete) => void;

class WebSocketService {
	private ws: WebSocket | null = null;
	private connectionPromise: Promise<void> | null = null;
	private isConnecting = false;
	private retryCount = 0;
	private maxRetries = 3;
	private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
	private pingInterval: ReturnType<typeof setInterval> | null = null;
	private userId: string | null = null;

	// Subscribers for different event types
	private executionUpdateCallbacks = new Map<
		string,
		Set<ExecutionUpdateCallback>
	>();
	private executionLogCallbacks = new Map<string, Set<ExecutionLogCallback>>();
	private newExecutionCallbacks = new Set<NewExecutionCallback>();
	private historyUpdateCallbacks = new Set<HistoryUpdateCallback>();
	private packageLogCallbacks = new Set<PackageLogCallback>();
	private packageCompleteCallbacks = new Set<PackageCompleteCallback>();

	// Track subscribed channels
	private subscribedChannels = new Set<string>();
	private pendingSubscriptions = new Set<string>();

	/**
	 * Connect to WebSocket with authentication
	 */
	async connect(channels: string[] = []): Promise<void> {
		// If already connected, just subscribe to new channels
		if (this.ws?.readyState === WebSocket.OPEN) {
			for (const channel of channels) {
				if (!this.subscribedChannels.has(channel)) {
					await this.subscribe(channel);
				}
			}
			return;
		}

		// If already connecting, wait for that connection
		if (this.isConnecting && this.connectionPromise) {
			await this.connectionPromise;
			// Subscribe to channels after connection
			for (const channel of channels) {
				if (!this.subscribedChannels.has(channel)) {
					await this.subscribe(channel);
				}
			}
			return;
		}

		this.isConnecting = true;
		this.pendingSubscriptions = new Set(channels);
		this.connectionPromise = this._connect(channels);

		try {
			await this.connectionPromise;
		} finally {
			this.isConnecting = false;
			this.connectionPromise = null;
		}
	}

	private async _connect(channels: string[]): Promise<void> {
		try {
			// Build WebSocket URL with channels
			const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
			const host = window.location.host;

			// Add channels as query params
			const params = new URLSearchParams();
			channels.forEach((ch) => params.append("channels", ch));

			const wsUrl = `${protocol}//${host}/ws/connect?${params.toString()}`;

			// Create WebSocket connection
			// Note: Cookies (including access_token) are automatically sent by the browser
			this.ws = new WebSocket(wsUrl);

			// Set up WebSocket handlers
			this.ws.onopen = () => {
				this.retryCount = 0;
				this.startPingInterval();
			};

			this.ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data) as WebSocketMessage;
					this.handleMessage(message);
				} catch (error) {
					console.error("[WebSocket] Failed to parse message:", error);
				}
			};

			this.ws.onerror = (error) => {
				console.error("[WebSocket] Error:", error);
			};

			this.ws.onclose = (event) => {
				this.ws = null;
				this.stopPingInterval();

				// Attempt to reconnect if not a normal closure
				if (event.code !== 1000 && this.retryCount < this.maxRetries) {
					this.retryCount++;
					const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
					this.reconnectTimeout = setTimeout(() => {
						this.connect(Array.from(this.subscribedChannels));
					}, delay);
				}
			};

			// Wait for connection to open
			await new Promise<void>((resolve, reject) => {
				const timeout = setTimeout(() => {
					reject(new Error("WebSocket connection timeout"));
				}, 10000);

				if (this.ws) {
					this.ws.addEventListener(
						"open",
						() => {
							clearTimeout(timeout);
							resolve();
						},
						{ once: true },
					);
					this.ws.addEventListener(
						"error",
						(error) => {
							clearTimeout(timeout);
							reject(error);
						},
						{ once: true },
					);
				}
			});
		} catch (error) {
			console.error("[WebSocket] Failed to connect:", error);
			this.ws = null;
			throw error;
		}
	}

	/**
	 * Connect to a specific execution
	 */
	async connectToExecution(executionId: string): Promise<void> {
		// If already connected to this execution, return
		const channel = `execution:${executionId}`;
		if (this.subscribedChannels.has(channel)) {
			return;
		}

		// If WebSocket is open, subscribe to channel
		if (this.ws?.readyState === WebSocket.OPEN) {
			await this.subscribe(channel);
			return;
		}

		// Otherwise, connect with this channel
		await this.connect([channel]);
	}

	/**
	 * Handle incoming WebSocket messages
	 */
	private handleMessage(message: WebSocketMessage) {
		switch (message.type) {
			case "connected":
				if ("channels" in message) {
					// General connection confirmation
					message.channels.forEach((ch) =>
						this.subscribedChannels.add(ch),
					);
					this.userId = message.userId;
				} else if ("executionId" in message) {
					// Execution-specific connection
					this.subscribedChannels.add(`execution:${message.executionId}`);
				}
				break;

			case "subscribed":
				this.subscribedChannels.add(message.channel);
				this.pendingSubscriptions.delete(message.channel);
				break;

			case "unsubscribed":
				this.subscribedChannels.delete(message.channel);
				break;

			case "pong":
				// Heartbeat response
				break;

			case "execution_update":
				this.dispatchExecutionUpdate(message);
				break;

			case "execution_log":
				this.dispatchExecutionLog(message);
				break;

			case "notification":
				// Handle notifications (future use)
				break;

			case "log":
				// Package installation log message
				this.packageLogCallbacks.forEach((cb) =>
					cb({ level: message.level, message: message.message }),
				);
				break;

			case "complete":
				// Package installation complete message
				this.packageCompleteCallbacks.forEach((cb) =>
					cb({ status: message.status, message: message.message }),
				);
				break;
		}
	}

	private dispatchExecutionUpdate(
		message: { type: "execution_update"; executionId: string } & Record<
			string,
			unknown
		>,
	) {
		const status = message["status"] as string;
		const timestamp =
			(message["timestamp"] as string) || new Date().toISOString();
		const result = message["result"];
		const error = message["error"] as string | undefined;
		const durationMs = message["duration_ms"] as number | undefined;

		const update: ExecutionUpdate = {
			executionId: message.executionId,
			status,
			isComplete:
				status === "Success" ||
				status === "Failed" ||
				status === "Timeout" ||
				status === "Cancelled",
			timestamp,
			result,
			...(error !== undefined ? { error } : {}),
			...(durationMs !== undefined ? { duration_ms: durationMs } : {}),
		};

		// Dispatch to execution-specific callbacks
		const callbacks = this.executionUpdateCallbacks.get(message.executionId);
		callbacks?.forEach((cb) => cb(update));

		// Dispatch to global callbacks (for history page)
		const completedAt = message["completed_at"] as string | undefined;
		const historyUpdate: HistoryUpdate = {
			execution_id: update.executionId,
			workflow_name: (message["workflow_name"] as string) || "",
			status: update.status,
			executed_by: (message["executed_by"] as string) || "",
			executed_by_name: (message["executed_by_name"] as string) || "",
			started_at: (message["started_at"] as string) || "",
			timestamp: update.timestamp,
			...(completedAt !== undefined ? { completed_at: completedAt } : {}),
			...(durationMs !== undefined ? { duration_ms: durationMs } : {}),
		};
		this.historyUpdateCallbacks.forEach((cb) => cb(historyUpdate));
	}

	private dispatchExecutionLog(
		message: { type: "execution_log"; executionId: string } & Record<
			string,
			unknown
		>,
	) {
		const sequence = message["sequence"] as number | undefined;
		const data = message["data"] as Record<string, unknown> | undefined;

		const log: ExecutionLog = {
			executionId: message.executionId,
			timestamp:
				(message["timestamp"] as string) || new Date().toISOString(),
			level: (message["level"] as string) || "info",
			message: (message["message"] as string) || "",
			...(sequence !== undefined ? { sequence } : {}),
			...(data !== undefined ? { data } : {}),
		};

		const callbacks = this.executionLogCallbacks.get(message.executionId);
		callbacks?.forEach((cb) => cb(log));
	}

	/**
	 * Subscribe to a channel
	 */
	async subscribe(channel: string): Promise<void> {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			this.pendingSubscriptions.add(channel);
			return;
		}

		this.ws.send(
			JSON.stringify({
				type: "subscribe",
				channels: [channel],
			}),
		);
	}

	/**
	 * Unsubscribe from a channel
	 */
	async unsubscribe(channel: string): Promise<void> {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			return;
		}

		this.ws.send(
			JSON.stringify({
				type: "unsubscribe",
				channel,
			}),
		);
	}

	/**
	 * Subscribe to execution updates for a specific execution
	 */
	onExecutionUpdate(
		executionId: string,
		callback: ExecutionUpdateCallback,
	): () => void {
		if (!this.executionUpdateCallbacks.has(executionId)) {
			this.executionUpdateCallbacks.set(executionId, new Set());
		}
		this.executionUpdateCallbacks.get(executionId)!.add(callback);

		// Return unsubscribe function
		return () => {
			this.executionUpdateCallbacks.get(executionId)?.delete(callback);
			if (this.executionUpdateCallbacks.get(executionId)?.size === 0) {
				this.executionUpdateCallbacks.delete(executionId);
			}
		};
	}

	/**
	 * Subscribe to execution logs for a specific execution
	 */
	onExecutionLog(
		executionId: string,
		callback: ExecutionLogCallback,
	): () => void {
		if (!this.executionLogCallbacks.has(executionId)) {
			this.executionLogCallbacks.set(executionId, new Set());
		}
		this.executionLogCallbacks.get(executionId)!.add(callback);

		// Return unsubscribe function
		return () => {
			this.executionLogCallbacks.get(executionId)?.delete(callback);
			if (this.executionLogCallbacks.get(executionId)?.size === 0) {
				this.executionLogCallbacks.delete(executionId);
			}
		};
	}

	/**
	 * Subscribe to new execution notifications
	 */
	onNewExecution(callback: NewExecutionCallback): () => void {
		this.newExecutionCallbacks.add(callback);
		return () => {
			this.newExecutionCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to history page updates
	 */
	onHistoryUpdate(callback: HistoryUpdateCallback): () => void {
		this.historyUpdateCallbacks.add(callback);
		return () => {
			this.historyUpdateCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to package installation logs
	 */
	onPackageLog(callback: PackageLogCallback): () => void {
		this.packageLogCallbacks.add(callback);
		return () => {
			this.packageLogCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to package installation completion
	 */
	onPackageComplete(callback: PackageCompleteCallback): () => void {
		this.packageCompleteCallbacks.add(callback);
		return () => {
			this.packageCompleteCallbacks.delete(callback);
		};
	}

	/**
	 * Start ping interval for keeping connection alive
	 */
	private startPingInterval() {
		this.pingInterval = setInterval(() => {
			if (this.ws?.readyState === WebSocket.OPEN) {
				this.ws.send(JSON.stringify({ type: "ping" }));
			}
		}, 30000);
	}

	/**
	 * Stop ping interval
	 */
	private stopPingInterval() {
		if (this.pingInterval) {
			clearInterval(this.pingInterval);
			this.pingInterval = null;
		}
	}

	/**
	 * Disconnect from WebSocket
	 */
	async disconnect(): Promise<void> {
		if (this.reconnectTimeout) {
			clearTimeout(this.reconnectTimeout);
			this.reconnectTimeout = null;
		}

		this.stopPingInterval();

		if (this.ws) {
			this.subscribedChannels.clear();
			this.ws.close(1000, "Normal closure");
			this.ws = null;
		}
	}

	/**
	 * Check if currently connected
	 */
	isConnected(): boolean {
		return this.ws?.readyState === WebSocket.OPEN;
	}

	/**
	 * Get the current user ID
	 */
	getUserId(): string | null {
		return this.userId;
	}
}

// Export singleton instance
export const webSocketService = new WebSocketService();

// Also export as webPubSubService for backwards compatibility
export const webPubSubService = webSocketService;
