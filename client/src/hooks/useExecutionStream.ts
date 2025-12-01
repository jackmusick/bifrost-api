/**
 * React hook for real-time execution updates via Azure Web PubSub
 *
 * Automatically connects to Web PubSub and subscribes to updates for a specific execution.
 * When the execution completes, it triggers a refetch of the full execution data.
 */

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { webPubSubService, type HistoryUpdate } from "@/services/webpubsub";
import {
	useExecutionStreamStore,
	type StreamingLog,
	type ExecutionStatus,
} from "@/stores/executionStreamStore";

interface UseExecutionStreamOptions {
	/**
	 * Execution ID to monitor
	 */
	executionId: string;

	/**
	 * Callback when execution completes
	 * Use this to trigger a refetch of full execution data
	 */
	onComplete?: (executionId: string) => void;

	/**
	 * Whether to enable streaming (default: true)
	 * Set to false to disable Web PubSub connection
	 */
	enabled?: boolean;
}

export function useExecutionStream(options: UseExecutionStreamOptions) {
	const { executionId, onComplete, enabled = true } = options;
	const [connectionError, setConnectionError] = useState<Error | null>(null);

	useEffect(() => {
		if (!enabled || !executionId) {
			return;
		}

		// Get store actions directly (they're stable references)
		const store = useExecutionStreamStore.getState();

		// Initialize stream in store if it doesn't exist
		const existingStream = store.streams[executionId];
		if (!existingStream) {
			store.startStreaming(executionId);
		}

		let unsubscribe: (() => void) | null = null;
		let currentGroupName: string | null = null;

		// Connect and subscribe
		const init = async () => {
			try {
				performance.mark(`pubsub-connect-start-${executionId}`);

				// Connect to Web PubSub
				await webPubSubService.connect();

				performance.mark(`pubsub-connect-end-${executionId}`);
				performance.measure(
					`pubsub-connect-${executionId}`,
					`pubsub-connect-start-${executionId}`,
					`pubsub-connect-end-${executionId}`,
				);

				// Check if actually connected (negotiate may have gracefully failed)
				if (!webPubSubService.isConnected()) {
					console.warn(
						`[useExecutionStream] Web PubSub not connected for ${executionId}`,
					);
					store.setConnectionStatus(executionId, false);
					return;
				}

				// Join the execution-specific group
				currentGroupName = `execution:${executionId}`;
				await webPubSubService.joinGroup(currentGroupName);

				store.setConnectionStatus(executionId, true);
				setConnectionError(null);

				// Subscribe to execution updates
				unsubscribe = webPubSubService.onExecutionUpdate((update) => {
					// Only process updates for THIS execution
					if (update["executionId"] === executionId) {
						// Get fresh store reference for each update
						const currentStore = useExecutionStreamStore.getState();

						// Update status if changed
						if (update.status) {
							currentStore.updateStatus(
								executionId,
								update.status as ExecutionStatus,
							);
						}

						// Append new logs
						if (update.latestLogs && update.latestLogs.length > 0) {
							const logs: StreamingLog[] = update.latestLogs.map(
								(log) => {
									const streamingLog: StreamingLog = {
										level: log.level,
										message: log.message,
										timestamp: log.timestamp,
									};
									if (log.sequence !== undefined) {
										streamingLog.sequence = log.sequence;
									}
									return streamingLog;
								},
							);
							currentStore.appendLogs(executionId, logs);
						}

						// If execution is complete, mark as complete in store
						if (update.isComplete) {
							currentStore.completeExecution(
								executionId,
								undefined,
								update.status as ExecutionStatus,
							);

							// Trigger callback for external refetch
							if (onComplete) {
								onComplete(executionId);
							}
						}
					}
				});
			} catch (error) {
				console.error("[useExecutionStream] Failed to connect:", error);
				const errorMessage =
					error instanceof Error ? error.message : String(error);
				store.setError(executionId, errorMessage);
				setConnectionError(
					error instanceof Error ? error : new Error(String(error)),
				);
				store.setConnectionStatus(executionId, false);
			}
		};

		init();

		// Cleanup on unmount or when executionId changes
		return () => {
			if (unsubscribe) {
				unsubscribe();
			}
			if (currentGroupName) {
				webPubSubService.leaveGroup(currentGroupName);
			}
			// NOTE: We don't call clearStream here because:
			// 1. It would cause infinite loops when currentExecutionId changes
			// 2. The consumer (RunPanel) should manage when to clear the stream
			// 3. Multiple components might be watching the same execution
		};
	}, [executionId, enabled, onComplete]);

	return {
		/**
		 * Whether Web PubSub is connected
		 */
		isConnected:
			useExecutionStreamStore.getState().streams[executionId]
				?.isConnected ?? false,

		/**
		 * Connection error (if any)
		 */
		connectionError,
	};
}

/**
 * React hook for monitoring new executions (for History screen)
 *
 * Automatically connects to Web PubSub and listens for new execution notifications.
 */
export function useNewExecutions(options: { enabled?: boolean } = {}) {
	const { enabled = true } = options;
	const [newExecutions, setNewExecutions] = useState<string[]>([]);
	const [isConnected, setIsConnected] = useState(false);

	useEffect(() => {
		if (!enabled) {
			return;
		}

		let unsubscribe: (() => void) | null = null;

		const init = async () => {
			try {
				await webPubSubService.connect();
				setIsConnected(true);

				// Subscribe to new execution notifications
				unsubscribe = webPubSubService.onNewExecution((execution) => {
					setNewExecutions((prev) => [
						execution.execution_id,
						...prev,
					]);
				});
			} catch (error) {
				console.error("[useNewExecutions] Failed to connect:", error);
				setIsConnected(false);
			}
		};

		init();

		return () => {
			if (unsubscribe) {
				unsubscribe();
			}
		};
	}, [enabled]);

	return {
		/**
		 * List of new execution IDs that have been created
		 */
		newExecutions,

		/**
		 * Whether Web PubSub is connected
		 */
		isConnected,

		/**
		 * Clear the list of new executions
		 */
		clearNewExecutions: () => setNewExecutions([]),
	};
}

/**
 * React hook for real-time history page updates
 *
 * Subscribes to a scope-specific history group and updates React Query cache
 * when new executions are created or existing ones complete.
 */
export function useExecutionHistory(
	options: { scope: string; enabled?: boolean } = { scope: "GLOBAL" },
) {
	const { scope, enabled = true } = options;
	const [isConnected, setIsConnected] = useState(false);
	const queryClient = useQueryClient();

	useEffect(() => {
		if (!enabled) {
			return;
		}

		let unsubscribe: (() => void) | null = null;
		let currentGroupName: string | null = null;

		const init = async () => {
			try {
				// Connect to Web PubSub
				await webPubSubService.connect();

				if (!webPubSubService.isConnected()) {
					setIsConnected(false);
					return;
				}

				// Join the scope-specific history group
				currentGroupName = `history:${scope}`;
				await webPubSubService.joinGroup(currentGroupName);

				setIsConnected(true);

				// Subscribe to history updates
				unsubscribe = webPubSubService.onHistoryUpdate(
					(update: HistoryUpdate) => {
						// Optimistically update ALL executions queries (handles different filters/pages)
						// We use setQueriesData to update all matching queries, but only for the first page
						const caches = queryClient.getQueriesData<{
							executions: Array<Record<string, unknown>>;
							continuationToken: string | null;
						}>({
							queryKey: ["executions"],
						});

						caches.forEach(([queryKey, oldData]) => {
							// Only update first page queries (no continuation token)
							const hasContinuationToken = queryKey[3]; // queryKey is ["executions", orgId, filters, continuationToken]
							if (hasContinuationToken || !oldData) return;

							const existingIndex = oldData.executions.findIndex(
								(exec) =>
									exec["execution_id"] ===
									update["execution_id"],
							);

							if (existingIndex >= 0) {
								// Update existing execution - React will handle reconciliation via key={execution_id}
								const newExecutions = [...oldData.executions];
								newExecutions[existingIndex] = {
									...newExecutions[existingIndex],
									status: update.status,
									completed_at: update.completed_at,
									duration_ms: update.duration_ms,
								};

								queryClient.setQueryData(queryKey, {
									...oldData,
									executions: newExecutions,
								});
							} else {
								// New execution - add to beginning of list (only if no filters active)
								const hasFilters =
									queryKey[2] &&
									Object.keys(queryKey[2]).length > 0;
								if (!hasFilters) {
									queryClient.setQueryData(queryKey, {
										...oldData,
										executions: [
											{
												execution_id:
													update.execution_id,
												workflow_name:
													update.workflow_name,
												status: update.status,
												executed_by: update.executed_by,
												executed_byName:
													update.executed_by_name,
												started_at: update.started_at,
												completed_at: update.completed_at,
												duration_ms: update.duration_ms,
											},
											...oldData.executions,
										],
									});
								}
							}
						});
					},
				);
			} catch (error) {
				console.error(
					"[useExecutionHistory] Failed to connect:",
					error,
				);
				setIsConnected(false);
			}
		};

		init();

		// Cleanup
		return () => {
			if (unsubscribe) {
				unsubscribe();
			}
			if (currentGroupName) {
				webPubSubService.leaveGroup(currentGroupName);
			}
		};
	}, [scope, enabled, queryClient]);

	return {
		/**
		 * Whether Web PubSub is connected for history updates
		 */
		isConnected,
	};
}
