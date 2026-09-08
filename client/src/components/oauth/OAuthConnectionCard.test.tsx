import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const mockToastSuccess = vi.fn();
const mockCopy = vi.hoisted(() => vi.fn());
vi.mock("@/lib/clipboard", () => ({ copyToClipboard: mockCopy }));
vi.mock("sonner", () => ({
	toast: {
		success: (...args: unknown[]) => mockToastSuccess(...args),
	},
}));

import { OAuthConnectionCard } from "./OAuthConnectionCard";
import type { components } from "@/lib/v1";

type OAuthConnectionDetail = components["schemas"]["OAuthConnectionDetail"];

function makeConnection(
	overrides: Partial<OAuthConnectionDetail> = {},
): OAuthConnectionDetail {
	return {
		connection_name: "connection-1",
		created_at: "2026-09-07T00:00:00Z",
		created_by: "fixture-user",
		updated_at: "2026-09-07T00:00:00Z",
		oauth_flow_type: "authorization_code",
		status: "not_connected",
		status_message: "Waiting for provider approval",
		client_id: "client-1",
		authorization_url: "https://auth.example.com",
		token_url: "https://token.example.com",
		scopes: "read",
		audience: "https://api.example.com",
		...overrides,
	};
}

describe("OAuthConnectionCard", () => {
	beforeEach(() => {
		mockToastSuccess.mockReset();
		mockCopy.mockReset().mockResolvedValue(true);
		Object.defineProperty(navigator, "clipboard", {
			configurable: true,
			value: {
				writeText: vi.fn().mockResolvedValue(undefined),
			},
		});
	});

	it("shows callback details and connects a non-connected authorization_code flow", async () => {
		const onAuthorize = vi.fn().mockResolvedValue(undefined);
		const onEdit = vi.fn();
		const onRefresh = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<OAuthConnectionCard
				connection={makeConnection()}
				onAuthorize={onAuthorize}
				onEdit={onEdit}
				onRefresh={onRefresh}
				onDelete={onDelete}
			/>,
		);

		expect(
			screen.getByRole("button", { name: "Copy callback URL" }),
		).toBeInTheDocument();
		expect(screen.getByText("Waiting for provider approval")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Connect" }),
		).toHaveClass("min-h-11");

		await user.click(screen.getByRole("button", { name: "Connect" }));
		expect(onAuthorize).toHaveBeenCalledWith("connection-1");
	});

	it("renders the refresh path and action menu for client credentials", async () => {
		const onAuthorize = vi.fn();
		const onEdit = vi.fn();
		const onRefresh = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<OAuthConnectionCard
				connection={makeConnection({
					oauth_flow_type: "client_credentials",
					status: "completed",
					expires_at: "2026-09-08T10:00:00",
				})}
				onAuthorize={onAuthorize}
				onEdit={onEdit}
				onRefresh={onRefresh}
				onDelete={onDelete}
			/>,
		);

		expect(
			screen.getByRole("button", { name: "Refresh Token" }),
		).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Connection actions" }));
		await user.click(screen.getByText("Edit"));
		expect(onEdit).toHaveBeenCalledWith("connection-1");
		await user.click(screen.getByRole("button", { name: "Connection actions" }));
		await user.click(screen.getByText("Delete"));
		expect(onDelete).toHaveBeenCalledWith("connection-1");
	});
	it("waits for copying and allows retry after a clipboard failure", async () => {
		let resolveCopy!: (value: boolean) => void;
		mockCopy.mockImplementationOnce(() => new Promise<boolean>((resolve) => { resolveCopy = resolve; }));
		const { user } = renderWithProviders(<OAuthConnectionCard connection={makeConnection()} onAuthorize={vi.fn()} onEdit={vi.fn()} onRefresh={vi.fn()} onDelete={vi.fn()} />);
		await user.click(screen.getByRole("button", { name: "Copy callback URL" }));
		expect(screen.getByRole("button", { name: "Copying callback URL" })).toBeDisabled();
		expect(mockToastSuccess).not.toHaveBeenCalled();
		resolveCopy(false);
		expect(await screen.findByRole("alert")).toHaveTextContent("Could not copy");
		expect(mockToastSuccess).not.toHaveBeenCalled();
		await user.click(screen.getByRole("button", { name: "Copy callback URL" }));
		await waitFor(() => expect(mockToastSuccess).toHaveBeenCalledTimes(1));
		expect(mockCopy).toHaveBeenLastCalledWith(`${window.location.origin}/oauth/callback/connection-1`);
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});

	it("ignores a copy completing after the card is unmounted", async () => {
		let resolveCopy!: (value: boolean) => void;
		mockCopy.mockImplementationOnce(() => new Promise<boolean>((resolve) => { resolveCopy = resolve; }));
		const { user, unmount } = renderWithProviders(<OAuthConnectionCard connection={makeConnection()} onAuthorize={vi.fn()} onEdit={vi.fn()} onRefresh={vi.fn()} onDelete={vi.fn()} />);
		await user.click(screen.getByRole("button", { name: "Copy callback URL" }));
		unmount();
		resolveCopy(true);
		await Promise.resolve();
		expect(mockToastSuccess).not.toHaveBeenCalled();
	});

});
