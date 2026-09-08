import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";
import { UserMCPConnections } from "./UserMCPConnections";

const mocks = vi.hoisted(() => ({
	queryClient: {
		invalidateQueries: vi.fn(),
	},
	useQuery: vi.fn(),
	get: vi.fn(),
	delete: vi.fn(),
}));

vi.mock("framer-motion", () => ({
	useReducedMotion: () => true,
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("@tanstack/react-query")>();
	return {
		...actual,
		useQueryClient: () => mocks.queryClient,
	};
});

vi.mock("@/lib/api-client", () => ({
	$api: {
		useQuery: (...args: unknown[]) => mocks.useQuery(...args),
	},
	apiClient: {
		GET: (...args: unknown[]) => mocks.get(...args),
		DELETE: (...args: unknown[]) => mocks.delete(...args),
	},
}));

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
		message: vi.fn(),
	},
}));

function makeQueryState<T>(
	overrides: Partial<{
		data: T;
		isLoading: boolean;
		isError: boolean;
		error: Error | null;
		refetch: ReturnType<typeof vi.fn>;
	}> = {},
) {
	return {
		data: undefined,
		isLoading: false,
		isError: false,
		error: null,
		refetch: vi.fn(),
		...overrides,
	};
}

beforeEach(() => {
	mocks.queryClient.invalidateQueries.mockReset();
	mocks.get.mockReset();
	mocks.delete.mockReset();
	mocks.useQuery.mockReset();
	vi.clearAllMocks();
});

afterEach(() => {
	vi.useRealTimers();
});

describe("UserMCPConnections", () => {
	it("refreshes definitions, server names and personal credential status together", async () => {
		const refresh = [vi.fn(), vi.fn(), vi.fn()];
		const paths = [
			"/api/mcp-connections",
			"/api/mcp-servers",
			"/api/me/mcp-connections",
		];
		mocks.useQuery.mockImplementation((_method: string, path: string) =>
			makeQueryState({ data: [], refetch: refresh[paths.indexOf(path)] }),
		);
		const { user } = renderWithProviders(<UserMCPConnections />);
		await user.click(screen.getByRole("button", { name: "Refresh" }));
		refresh.forEach((refetch) => expect(refetch).toHaveBeenCalledTimes(1));
	});

	it("shows cached rows when a query fails and offers retry", async () => {
		const retryConnections = vi.fn();
		const retryServers = vi.fn();
		const retryCreds = vi.fn();

		mocks.useQuery.mockImplementation((_method: string, path: string) => {
			if (path === "/api/mcp-connections") {
				return makeQueryState({
					data: [
						{
							id: "conn-1",
							server_id: "srv-1",
							available_in_chat: true,
							available_to_autonomous: false,
							service_oauth_token_id: null,
						},
					],
					isError: true,
					error: new Error("offline"),
					refetch: retryConnections,
				});
			}
			if (path === "/api/mcp-servers") {
				return makeQueryState({
					data: [{ id: "srv-1", name: "GitHub" }],
					refetch: retryServers,
				});
			}
			return makeQueryState({
				data: [
					{
						connection_id: "conn-1",
						consent_granted_at: "2026-09-08T12:00:00Z",
						consent_expires_at: null,
					},
				],
				refetch: retryCreds,
			});
		});

		renderWithProviders(<UserMCPConnections />);

		expect(await screen.findByRole("alert")).toHaveTextContent(
			/previously loaded records are shown below/i,
		);
		expect(screen.getAllByText("GitHub")[0]).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /retry loading/i }),
		).toBeEnabled();

		fireEvent.click(screen.getByRole("button", { name: /retry loading/i }));

		await waitFor(() => {
			expect(retryConnections).toHaveBeenCalled();
			expect(retryServers).toHaveBeenCalled();
			expect(retryCreds).toHaveBeenCalled();
		});
	});

	it("keeps connect pending until success or popup dismissal", async () => {
		let resolveGet!: (value: {
			data: { authorization_url: string };
		}) => void;
		const popup = {
			close: vi.fn(),
		} as unknown as Window;
		const openSpy = vi.spyOn(window, "open").mockReturnValue(popup);

		mocks.useQuery.mockImplementation((_method: string, path: string) => {
			if (path === "/api/mcp-connections") {
				return makeQueryState({
					data: [
						{
							id: "conn-1",
							server_id: "srv-1",
							available_in_chat: true,
							available_to_autonomous: false,
							service_oauth_token_id: null,
						},
					],
				});
			}
			if (path === "/api/mcp-servers") {
				return makeQueryState({
					data: [{ id: "srv-1", name: "GitHub" }],
				});
			}
			return makeQueryState({
				data: [],
			});
		});

		mocks.get.mockImplementation(() => {
			return new Promise((resolve) => {
				resolveGet = resolve;
			});
		});

		renderWithProviders(<UserMCPConnections />);

		const connectButton = screen.getAllByRole("button", {
			name: "Connect",
		})[0];
		fireEvent.click(connectButton);

		expect(connectButton).toBeDisabled();
		expect(mocks.get).toHaveBeenCalledTimes(1);

		resolveGet({
			data: { authorization_url: "https://example.test/auth" },
		});

		await waitFor(() => {
			expect(openSpy).toHaveBeenCalledWith(
				"https://example.test/auth",
				"mcp_user_oauth",
				"width=600,height=720",
			);
		});
		expect(
			screen.getAllByRole("button", { name: /connecting/i })[0],
		).toBeDisabled();

		await act(async () => {
			fireEvent.click(connectButton);
		});
		expect(mocks.get).toHaveBeenCalledTimes(1);

		window.dispatchEvent(
			new MessageEvent("message", {
				origin: window.location.origin,
				data: {
					type: "mcp_oauth_success",
					connection_id: "conn-1",
				},
			}),
		);

		await waitFor(() => {
			expect(mocks.queryClient.invalidateQueries).toHaveBeenCalledWith({
				queryKey: ["get", "/api/mcp-connections"],
			});
			expect(mocks.queryClient.invalidateQueries).toHaveBeenCalledWith({
				queryKey: ["get", "/api/me/mcp-connections"],
			});
			expect(popup.close).toHaveBeenCalled();
			expect(
				screen.getAllByRole("button", { name: "Connect" })[0],
			).toBeEnabled();
		});

		openSpy.mockRestore();
	});

	it("clears connect state when the popup reports an error", async () => {
		let resolveGet!: (value: {
			data: { authorization_url: string };
		}) => void;
		const popup = {
			close: vi.fn(),
		} as unknown as Window;
		const openSpy = vi.spyOn(window, "open").mockReturnValue(popup);

		mocks.useQuery.mockImplementation((_method: string, path: string) => {
			if (path === "/api/mcp-connections") {
				return makeQueryState({
					data: [
						{
							id: "conn-1",
							server_id: "srv-1",
							available_in_chat: true,
							available_to_autonomous: false,
							service_oauth_token_id: null,
						},
					],
				});
			}
			if (path === "/api/mcp-servers") {
				return makeQueryState({
					data: [{ id: "srv-1", name: "GitHub" }],
				});
			}
			return makeQueryState({
				data: [],
			});
		});

		mocks.get.mockImplementation(() => {
			return new Promise((resolve) => {
				resolveGet = resolve;
			});
		});

		renderWithProviders(<UserMCPConnections />);

		fireEvent.click(screen.getAllByRole("button", { name: "Connect" })[0]);
		resolveGet({
			data: { authorization_url: "https://example.test/auth" },
		});

		await waitFor(() => {
			expect(openSpy).toHaveBeenCalled();
		});

		window.dispatchEvent(
			new MessageEvent("message", {
				origin: window.location.origin,
				data: {
					type: "mcp_oauth_error",
					connection_id: "conn-1",
					error: "access_denied",
				},
			}),
		);

		await waitFor(() => {
			expect(
				screen.getAllByText("Connection failed: access_denied")[0],
			).toBeInTheDocument();
			expect(
				screen.getAllByRole("button", { name: "Connect" })[0],
			).toBeEnabled();
			expect(popup.close).toHaveBeenCalled();
		});

		openSpy.mockRestore();
	});

	it("clears a blocked popup and reports the failure", async () => {
		let resolveGet!: (value: {
			data: { authorization_url: string };
		}) => void;
		const openSpy = vi.spyOn(window, "open").mockReturnValue(null);

		mocks.useQuery.mockImplementation((_method: string, path: string) => {
			if (path === "/api/mcp-connections") {
				return makeQueryState({
					data: [
						{
							id: "conn-1",
							server_id: "srv-1",
							available_in_chat: true,
							available_to_autonomous: false,
							service_oauth_token_id: null,
						},
					],
				});
			}
			if (path === "/api/mcp-servers") {
				return makeQueryState({
					data: [{ id: "srv-1", name: "GitHub" }],
				});
			}
			return makeQueryState({
				data: [],
			});
		});

		mocks.get.mockImplementation(() => {
			return new Promise((resolve) => {
				resolveGet = resolve;
			});
		});

		renderWithProviders(<UserMCPConnections />);

		fireEvent.click(screen.getAllByRole("button", { name: "Connect" })[0]);
		resolveGet({
			data: { authorization_url: "https://example.test/auth" },
		});

		await waitFor(() => {
			expect(
				screen.getAllByText(
					"Popup blocked — please allow popups for this site and try again",
				)[0],
			).toBeInTheDocument();
			expect(
				screen.getAllByRole("button", { name: "Connect" })[0],
			).toBeEnabled();
		});

		expect(openSpy).toHaveBeenCalled();
		openSpy.mockRestore();
	});

	it("shows an inline disconnect error and lets the user retry", async () => {
		mocks.useQuery.mockImplementation((_method: string, path: string) => {
			if (path === "/api/mcp-connections") {
				return makeQueryState({
					data: [
						{
							id: "conn-1",
							server_id: "srv-1",
							available_in_chat: true,
							available_to_autonomous: false,
							service_oauth_token_id: null,
						},
					],
				});
			}
			if (path === "/api/mcp-servers") {
				return makeQueryState({
					data: [{ id: "srv-1", name: "Calendar" }],
				});
			}
			return makeQueryState({
				data: [
					{
						connection_id: "conn-1",
						consent_granted_at: null,
						consent_expires_at: null,
					},
				],
			});
		});

		mocks.delete.mockRejectedValueOnce(new Error("Network unavailable"));
		mocks.delete.mockResolvedValueOnce({ data: undefined, error: null });

		renderWithProviders(<UserMCPConnections />);

		const disconnectButton = screen.getAllByRole("button", {
			name: "Disconnect",
		})[0];
		fireEvent.click(disconnectButton);

		await waitFor(() => {
			expect(screen.getAllByRole("alert")[0]).toHaveTextContent(
				/failed to disconnect calendar/i,
			);
			expect(
				screen.getAllByRole("button", { name: /retry disconnect/i })[0],
			).toBeEnabled();
		});

		fireEvent.click(
			screen.getAllByRole("button", { name: /retry disconnect/i })[0],
		);

		await waitFor(() => {
			expect(mocks.delete).toHaveBeenCalledTimes(2);
			expect(mocks.queryClient.invalidateQueries).toHaveBeenCalledWith({
				queryKey: ["get", "/api/me/mcp-connections"],
			});
			expect(
				screen.queryByText(/failed to disconnect calendar/i),
			).not.toBeInTheDocument();
		});
	});
});
