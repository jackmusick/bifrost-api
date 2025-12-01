/**
 * Azure Web PubSub Service for real-time execution updates
 *
 * Uses native WebSocket with JSON protocol (much simpler than SignalR!)
 *
 * Provides connection management and event subscriptions for:
 * - Execution status updates (for execution details screen)
 * - New execution notifications (for history screen)
 */

export interface ExecutionUpdate {
	executionId: string;
	status: string;
	isComplete: boolean;
	timestamp: string;
	latestLogs?: Array<{
		timestamp: string;
		level: string;
		message: string;
		sequence?: number; // Sequence number for client-side reordering
		data?: Record<string, unknown>;
	}>;
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

export interface PackageLogMessage {
	type: "log";
	level: string;
	message: string;
}

export interface PackageCompleteMessage {
	type: "complete";
	status: "success" | "error" | "conflict";
	message: string;
}

type PackageMessage = PackageLogMessage | PackageCompleteMessage;

type ExecutionUpdateCallback = (update: ExecutionUpdate) => void;
type NewExecutionCallback = (execution: NewExecution) => void;
type HistoryUpdateCallback = (update: HistoryUpdate) => void;
type PackageMessageCallback = (message: PackageMessage) => void;

class WebPubSubService {
	private ws: WebSocket | null = null;
	private connectionPromise: Promise<void> | null = null;
	private isConnecting = false;
	private retryCount = 0;
	private maxRetries = 3;
	private reconnectTimeout: NodeJS.Timeout | null = null;
	private connectionId: string | null = null;

	// Subscribers for different event types
	private executionUpdateCallbacks = new Set<ExecutionUpdateCallback>();
	private newExecutionCallbacks = new Set<NewExecutionCallback>();
	private historyUpdateCallbacks = new Set<HistoryUpdateCallback>();
	private packageMessageCallbacks = new Set<PackageMessageCallback>();

	// Track subscribed groups
	private subscribedGroups = new Set<string>();

	/**
	 * Connect to Web PubSub with authentication
	 */
	async connect(): Promise<void> {
		// If already connected, return immediately
		if (this.ws?.readyState === WebSocket.OPEN) {
			return;
		}

		// If already connecting, wait for that connection
		if (this.isConnecting && this.connectionPromise) {
			return this.connectionPromise;
		}

		this.isConnecting = true;
		this.connectionPromise = this._connect();

		try {
			await this.connectionPromise;
		} finally {
			this.isConnecting = false;
			this.connectionPromise = null;
		}
	}

	private async _connect(): Promise<void> {
		try {
			// Negotiate connection with backend to get WebSocket URL
			const response = await fetch("/api/webpubsub/negotiate", {
				method: "POST",
				credentials: "include", // Include auth cookies
			});

			if (!response.ok) {
				// If Web PubSub is not configured, gracefully fall back to polling
				if (response.status === 503) {
					this.ws = null;
					return; // Graceful exit
				}
				throw new Error(
					`Failed to negotiate Web PubSub connection: ${response.statusText}`,
				);
			}

			const connectionInfo = await response.json();

			// Create WebSocket connection
			this.ws = new WebSocket(
				connectionInfo.url,
				"json.webpubsub.azure.v1",
			);

			// Set up WebSocket handlers
			this.ws.onopen = () => {
				this.retryCount = 0;

				// Resubscribe to groups after reconnect
				this.resubscribeGroups();
			};

			this.ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					this.handleMessage(message);
				} catch (error) {
					console.error(
						"[WebPubSub] Failed to parse message:",
						error,
					);
				}
			};

			this.ws.onerror = (error) => {
				console.error("[WebPubSub] WebSocket error:", error);
			};

			this.ws.onclose = (event) => {
				this.ws = null;

				// Attempt to reconnect if not a normal closure
				if (event.code !== 1000 && this.retryCount < this.maxRetries) {
					this.retryCount++;
					this.reconnectTimeout = setTimeout(
						() => this.connect(),
						5000,
					);
				}
			};

			// Wait for connection to open
			await new Promise<void>((resolve, reject) => {
				const timeout = setTimeout(() => {
					reject(new Error("WebSocket connection timeout"));
				}, 10000);

				if (this.ws) {
					this.ws.addEventListener("open", () => {
						clearTimeout(timeout);
						resolve();
					});
					this.ws.addEventListener("error", (error) => {
						clearTimeout(timeout);
						reject(error);
					});
				}
			});
		} catch (error) {
			console.error("[WebPubSub] Failed to connect:", error);
			this.ws = null;
			throw error;
		}
	}

	/**
	 * Handle incoming Web PubSub messages
	 */
	private handleMessage(message: unknown) {
		// Type guard for message structure
		if (typeof message !== "object" || message === null) {
			return;
		}

		const msg = message as Record<string, unknown>;

		// Web PubSub system messages
		if (msg["type"] === "system") {
			if (msg["event"] === "connected") {
				const connId = (msg as { connectionId?: string }).connectionId;
				if (connId) {
					this.connectionId = connId;
				}
			}
			return;
		}

		// Application messages from server
		if (msg["type"] === "message") {
			const data = msg["data"] as Record<string, unknown>;

			// Check message target and dispatch to appropriate callbacks
			if (data["target"] === "executionUpdate") {
				this.executionUpdateCallbacks.forEach((cb) =>
					cb(data["data"] as ExecutionUpdate),
				);
			} else if (data["target"] === "newExecution") {
				this.newExecutionCallbacks.forEach((cb) =>
					cb(data["data"] as NewExecution),
				);
			} else if (data["target"] === "executionHistoryUpdate") {
				this.historyUpdateCallbacks.forEach((cb) =>
					cb(data["data"] as HistoryUpdate),
				);
			} else if (data["type"] === "log" || data["type"] === "complete") {
				// Package installation messages (sent directly to connection, not via group)
				// Validate and cast the message
				if (this.isPackageMessage(data)) {
					this.packageMessageCallbacks.forEach((cb) => cb(data));
				}
			}
		}
	}

	/**
	 * Type guard to validate PackageMessage
	 */
	private isPackageMessage(data: unknown): data is PackageMessage {
		if (typeof data !== "object" || data === null) {
			return false;
		}
		const obj = data as Record<string, unknown>;
		if (obj["type"] === "log") {
			return (
				typeof obj["level"] === "string" &&
				typeof obj["message"] === "string"
			);
		} else if (obj["type"] === "complete") {
			return (
				(obj["status"] === "success" ||
					obj["status"] === "error" ||
					obj["status"] === "conflict") &&
				typeof obj["message"] === "string"
			);
		}
		return false;
	}

	/**
	 * Join a group to receive messages
	 */
	async joinGroup(groupName: string): Promise<void> {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			return;
		}

		// Send join group command
		const command = {
			type: "joinGroup",
			group: groupName,
		};

		this.ws.send(JSON.stringify(command));
		this.subscribedGroups.add(groupName);
	}

	/**
	 * Leave a group
	 */
	async leaveGroup(groupName: string): Promise<void> {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			return;
		}

		const command = {
			type: "leaveGroup",
			group: groupName,
		};

		this.ws.send(JSON.stringify(command));
		this.subscribedGroups.delete(groupName);
	}

	/**
	 * Resubscribe to all groups after reconnect
	 */
	private resubscribeGroups() {
		this.subscribedGroups.forEach((group) => {
			this.joinGroup(group);
		});
	}

	/**
	 * Subscribe to execution updates
	 *
	 * @param callback - Function to call when execution updates are received
	 * @returns Unsubscribe function
	 */
	onExecutionUpdate(callback: ExecutionUpdateCallback): () => void {
		this.executionUpdateCallbacks.add(callback);

		// Return unsubscribe function
		return () => {
			this.executionUpdateCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to new execution notifications
	 *
	 * @param callback - Function to call when new executions start
	 * @returns Unsubscribe function
	 */
	onNewExecution(callback: NewExecutionCallback): () => void {
		this.newExecutionCallbacks.add(callback);

		// Return unsubscribe function
		return () => {
			this.newExecutionCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to history page updates (new executions and completions)
	 *
	 * @param callback - Function to call when execution history updates arrive
	 * @returns Unsubscribe function
	 */
	onHistoryUpdate(callback: HistoryUpdateCallback): () => void {
		this.historyUpdateCallbacks.add(callback);

		// Return unsubscribe function
		return () => {
			this.historyUpdateCallbacks.delete(callback);
		};
	}

	/**
	 * Subscribe to package installation messages
	 *
	 * @param callback - Function to call when package messages arrive
	 * @returns Unsubscribe function
	 */
	onPackageMessage(callback: PackageMessageCallback): () => void {
		this.packageMessageCallbacks.add(callback);

		// Return unsubscribe function
		return () => {
			this.packageMessageCallbacks.delete(callback);
		};
	}

	/**
	 * Disconnect from Web PubSub
	 */
	async disconnect(): Promise<void> {
		if (this.reconnectTimeout) {
			clearTimeout(this.reconnectTimeout);
			this.reconnectTimeout = null;
		}

		if (this.ws) {
			this.subscribedGroups.clear();
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
	 * Get the current connection ID
	 */
	getConnectionId(): string | null {
		return this.connectionId;
	}
}

// Export singleton instance
export const webPubSubService = new WebPubSubService();
