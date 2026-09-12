import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mock = vi.hoisted(() => ({
	connected: false,
	listeners: new Set<(connected: boolean) => void>(),
	updates: new Map<string, (update: EventSourceUpdate) => void>(),
	connect: vi.fn(),
	unsubscribe: vi.fn(),
}));
vi.mock("@/services/websocket", () => ({
	webSocketService: {
		connect: mock.connect,
		unsubscribe: mock.unsubscribe,
		isConnected: () => mock.connected,
		onConnectionStatusChange: (listener: (connected: boolean) => void) => {
			mock.listeners.add(listener);
			return () => mock.listeners.delete(listener);
		},
		onEventSourceUpdate: (
			sourceId: string,
			callback: (update: EventSourceUpdate) => void,
		) => {
			mock.updates.set(sourceId, callback);
			return () => mock.updates.delete(sourceId);
		},
	},
}));
import { useEventStream } from "./useEventStream";
import type { EventSourceUpdate } from "@/services/websocket";

function createWrapper(client = new QueryClient()) {
	return function Wrapper({ children }: { children: ReactNode }) {
		return (
			<QueryClientProvider client={client}>
				{children}
			</QueryClientProvider>
		);
	};
}
beforeEach(() => {
	mock.connected = false;
	mock.listeners.clear();
	mock.updates.clear();
	mock.connect.mockReset().mockResolvedValue(undefined);
	mock.unsubscribe.mockReset().mockResolvedValue(undefined);
});
function reportConnection(connected: boolean) {
	act(() => {
		mock.connected = connected;
		mock.listeners.forEach((listener) => listener(connected));
	});
}
describe("event streaming connection state", () => {
	it("clears Live on disconnect and restores it on reconnect", async () => {
		mock.connected = true;
		const { result, unmount } = renderHook(
			() => useEventStream("source-1"),
			{ wrapper: createWrapper() },
		);
		await waitFor(() => expect(result.current.isConnected).toBe(true));
		reportConnection(false);
		expect(result.current.isConnected).toBe(false);
		reportConnection(true);
		expect(result.current.isConnected).toBe(true);
		unmount();
		expect(mock.listeners.size).toBe(0);
	});
	it("handles a rejected initial connection without claiming Live", async () => {
		mock.connect.mockRejectedValue(new Error("Connection unavailable"));
		const { result } = renderHook(() => useEventStream("source-1"), {
			wrapper: createWrapper(),
		});
		await act(async () => {
			await Promise.resolve();
		});
		expect(result.current.isConnected).toBe(false);
		reportConnection(true);
		expect(result.current.isConnected).toBe(true);
	});
	it("ignores a late connection resolution from a previous source", async () => {
		let resolveOld!: () => void;
		let resolveCurrent!: () => void;
		mock.connect
			.mockReturnValueOnce(
				new Promise<void>((resolve) => {
					resolveOld = resolve;
				}),
			)
			.mockReturnValueOnce(
				new Promise<void>((resolve) => {
					resolveCurrent = resolve;
				}),
			);
		const { result, rerender } = renderHook(
			({ source }) => useEventStream(source),
			{
				wrapper: createWrapper(),
				initialProps: { source: "source-1" },
			},
		);
		rerender({ source: "source-2" });
		mock.connected = true;
		await act(async () => {
			resolveOld();
		});
		expect(result.current.isConnected).toBe(false);
		await act(async () => {
			resolveCurrent();
		});
		expect(result.current.isConnected).toBe(true);
	});
	it("refreshes the source count and list when a new event arrives", () => {
		const client = new QueryClient();
		const sourceKey = (id: string) => [
			"get",
			"/api/events/sources/{source_id}",
			{ params: { path: { source_id: id } } },
		];
		const listKey = [
			"get",
			"/api/events/sources",
			{ params: { query: { limit: 100 } } },
		];
		client.setQueryData(sourceKey("source-1"), { event_count_24h: 1 });
		client.setQueryData(sourceKey("source-2"), { event_count_24h: 5 });
		client.setQueryData(listKey, []);
		renderHook(() => useEventStream("source-1"), {
			wrapper: createWrapper(client),
		});
		act(() =>
			mock.updates.get("source-1")?.({
				type: "event_created",
				event: {
					id: "event-2",
					event_source_id: "source-1",
					event_type: "order.created",
					status: "received",
					received_at: null,
					source_ip: null,
					delivery_count: 0,
					success_count: 0,
					failed_count: 0,
				},
			}),
		);
		expect(client.getQueryState(sourceKey("source-1"))?.isInvalidated).toBe(
			true,
		);
		expect(client.getQueryState(sourceKey("source-2"))?.isInvalidated).toBe(
			false,
		);
		expect(client.getQueryState(listKey)?.isInvalidated).toBe(true);
	});
});
