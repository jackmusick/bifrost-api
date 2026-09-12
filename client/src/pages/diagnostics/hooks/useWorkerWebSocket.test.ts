import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkerWebSocket } from "./useWorkerWebSocket";

const socket = vi.hoisted(() => ({
	connected: true,
	listener: undefined as ((connected: boolean) => void) | undefined,
	stopStatus: vi.fn(),
	stopMessages: vi.fn(),
	unsubscribe: vi.fn(),
}));
vi.mock("@/services/websocket", () => ({
	webSocketService: {
		connect: vi.fn().mockResolvedValue(undefined),
		isConnected: () => socket.connected,
		onConnectionStatusChange: (listener: (connected: boolean) => void) => {
			socket.listener = listener;
			return socket.stopStatus;
		},
		onPoolMessage: () => socket.stopMessages,
		unsubscribe: socket.unsubscribe,
	},
}));

describe("useWorkerWebSocket connection state", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		socket.connected = true;
	});
	it("tracks disconnection and reconnection after the initial subscription and cleans up", async () => {
		const { result, unmount } = renderHook(() => useWorkerWebSocket());
		await waitFor(() => expect(result.current.isConnected).toBe(true));
		act(() => {
			socket.connected = false;
			socket.listener?.(false);
		});
		expect(result.current.isConnected).toBe(false);
		act(() => {
			socket.connected = true;
			socket.listener?.(true);
		});
		expect(result.current.isConnected).toBe(true);
		unmount();
		expect(socket.stopStatus).toHaveBeenCalledOnce();
		expect(socket.stopMessages).toHaveBeenCalledOnce();
		expect(socket.unsubscribe).toHaveBeenCalledWith("platform_workers");
	});
});
