/**
 * Hook for real-time event streaming via WebSocket
 *
 * Subscribes to event source updates and automatically updates
 * React Query cache with new events.
 */

import { useEffect, useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { webSocketService, type EventSourceUpdate } from "@/services/websocket";

interface UseEventStreamOptions {
	enabled?: boolean;
}

export function useEventStream(
	sourceId: string | undefined,
	options: UseEventStreamOptions = {},
) {
	const { enabled = true } = options;
	const queryClient = useQueryClient();
	const [isConnected, setIsConnected] = useState(false);

	const handleUpdate = useCallback(
		(update: EventSourceUpdate) => {
			if (!sourceId) return;

			if (update.type === "event_created") {
				// Refresh counts alongside the newly received event.
				void queryClient.invalidateQueries({
					queryKey: [
						"get",
						"/api/events/sources/{source_id}",
						{ params: { path: { source_id: sourceId } } },
					],
				});
				void queryClient.invalidateQueries({
					queryKey: ["get", "/api/events/sources"],
				});
			}

			// Invalidate events queries to trigger refetch
			// Using partial key match so it works regardless of filter params
			if (
				update.type === "event_created" ||
				update.type === "event_updated"
			) {
				// Invalidate events list
				queryClient.invalidateQueries({
					queryKey: ["get", "/api/events/sources/{source_id}/events"],
				});

				// Also invalidate individual event queries so detail dialogs update
				queryClient.invalidateQueries({
					predicate: (query) =>
						query.queryKey[0] === "get" &&
						query.queryKey[1] === "/api/events/{event_id}",
				});

				// Invalidate deliveries queries so delivery status updates in dialog
				queryClient.invalidateQueries({
					predicate: (query) =>
						query.queryKey[0] === "get" &&
						query.queryKey[1] ===
							"/api/events/{event_id}/deliveries",
				});
			}
		},
		[sourceId, queryClient],
	);

	// Manage WebSocket connection
	useEffect(() => {
		// Skip if not enabled or no sourceId
		if (!sourceId || !enabled) {
			return;
		}

		const channel = `event-source:${sourceId}`;
		let active = true;
		const unsubscribeStatus = webSocketService.onConnectionStatusChange(
			(connected) => {
				if (active) setIsConnected(connected);
			},
		);

		// Connect to WebSocket with the event source channel
		void webSocketService
			.connect([channel])
			.then(() => {
				if (active) setIsConnected(webSocketService.isConnected());
			})
			.catch(() => {
				if (active) setIsConnected(false);
			});

		// Subscribe to updates
		const unsubscribe = webSocketService.onEventSourceUpdate(
			sourceId,
			handleUpdate,
		);

		return () => {
			active = false;
			unsubscribeStatus();
			unsubscribe();
			// Unsubscribe from channel
			void webSocketService.unsubscribe(channel).catch(() => {});
			setIsConnected(false);
		};
	}, [sourceId, enabled, handleUpdate]);

	// If not enabled or no sourceId, connection is always false
	const effectiveIsConnected = sourceId && enabled ? isConnected : false;

	return {
		isConnected: effectiveIsConnected,
	};
}
