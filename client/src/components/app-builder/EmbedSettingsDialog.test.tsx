import type { HTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";

const mockAuthFetch = vi.hoisted(() => vi.fn());
const mockCopyToClipboard = vi.hoisted(() => vi.fn());
const mockToast = vi.hoisted(() => ({
	success: vi.fn(),
	error: vi.fn(),
}));

vi.mock("sonner", () => ({
	toast: mockToast,
}));

vi.mock("@/lib/api-client", () => ({
	authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

vi.mock("@/lib/clipboard", () => ({
	copyToClipboard: (...args: unknown[]) => mockCopyToClipboard(...args),
}));

vi.mock("react-syntax-highlighter", () => ({
	Prism: ({ children }: { children: ReactNode }) => (
		<pre data-testid="snippet">{children}</pre>
	),
}));

vi.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
	oneDark: {},
}));

vi.mock("framer-motion", () => ({
	AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
	motion: {
		div: (props: HTMLAttributes<HTMLDivElement>) => <div {...props} />,
	},
}));

import { EmbedSettingsDialog } from "./EmbedSettingsDialog";

function makeResponse(body: unknown, ok = true, text = "") {
	return {
		ok,
		json: async () => body,
		text: async () => text,
	} as Response;
}

function renderDialog(open = true) {
	return renderWithProviders(
		<EmbedSettingsDialog
			appId="app-1"
			appSlug="sample-app"
			open={open}
			onOpenChange={vi.fn()}
		/>,
	);
}

beforeEach(() => {
	mockAuthFetch.mockReset();
	mockCopyToClipboard.mockReset();
	mockToast.success.mockReset();
	mockToast.error.mockReset();
});

afterEach(() => {
	vi.useRealTimers();
});

describe("EmbedSettingsDialog", () => {
	it("shows the loading state while secrets are fetched", async () => {
		mockAuthFetch.mockReturnValue(new Promise(() => {}));

		renderDialog();

		expect(await screen.findByRole("status")).toHaveTextContent(
			/Loading embed secrets/i,
		);
	});

	it("shows a load error and retries the query", async () => {
		mockAuthFetch
			.mockRejectedValueOnce(new Error("offline"))
			.mockResolvedValueOnce(makeResponse([]));

		const { user } = renderDialog();

		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent(/couldn’t load embed secrets/i);
		expect(alert).toHaveTextContent("offline");

		await user.click(screen.getByRole("button", { name: /retry/i }));

		await waitFor(() => {
			expect(screen.getByText(/no embed secrets configured/i)).toBeInTheDocument();
		});
	});

	it("creates a secret, closes the create dialog, and reveals the raw secret", async () => {
		const created = {
			id: "secret-1",
			name: "Production",
			is_active: true,
			hmac_scheme: "shopify",
			created_at: "2026-09-07T12:00:00.000Z",
			raw_secret: "raw-secret-value",
		};
		mockAuthFetch
			.mockResolvedValueOnce(makeResponse([]))
			.mockResolvedValueOnce(makeResponse(created))
			.mockResolvedValueOnce(makeResponse([]));
		mockCopyToClipboard.mockResolvedValueOnce(true);

		const { user } = renderDialog();

		await screen.findByText(/no embed secrets configured/i);
		await user.click(screen.getByRole("button", { name: /create secret/i }));

		const createDialog = await screen.findByRole("dialog", {
			name: /create embed secret/i,
		});
		await user.type(within(createDialog).getByLabelText(/^name$/i), "Production");
		await user.type(
			within(createDialog).getByLabelText(/secret \(optional\)/i),
			"raw-secret-value",
		);

		await user.click(within(createDialog).getByRole("button", { name: /create secret/i }));

		const createdDialog = await screen.findByRole("dialog", {
			name: /secret created/i,
		});
		expect(within(createdDialog).getByText(/copy this secret now/i)).toBeVisible();
		expect(within(createdDialog).getByText("raw-secret-value")).toBeInTheDocument();

		await user.click(
			within(createdDialog).getByRole("button", { name: /copy raw secret/i }),
		);
		await waitFor(() => {
			expect(mockCopyToClipboard).toHaveBeenCalledWith("raw-secret-value");
		});
		expect(mockToast.success).toHaveBeenCalledWith("Copied raw secret");

		expect(
			mockAuthFetch.mock.calls.some(
				([url, init]) =>
					url === "/api/applications/app-1/embed-secrets" &&
					(init as RequestInit | undefined)?.method === "POST",
			),
		).toBe(true);
		expect(mockToast.success).toHaveBeenCalledWith("Embed secret created");
	});

	it("keeps the create inputs visible when creation fails", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(makeResponse([]))
			.mockRejectedValueOnce(new Error("create failed"));

		const { user } = renderDialog();

		await screen.findByText(/no embed secrets configured/i);
		await user.click(screen.getByRole("button", { name: /create secret/i }));

		const createDialog = await screen.findByRole("dialog", {
			name: /create embed secret/i,
		});
		const nameInput = within(createDialog).getByLabelText(/^name$/i);
		const secretInput = within(createDialog).getByLabelText(/secret \(optional\)/i);

		await user.type(nameInput, "Production");
		await user.type(secretInput, "raw-secret-value");
		await user.click(within(createDialog).getByRole("button", { name: /create secret/i }));

		await waitFor(() => {
			expect(mockToast.error).toHaveBeenCalledWith("Failed to create embed secret");
		});
		expect(within(createDialog).getByRole("alert")).toHaveTextContent("Your values are preserved");
		expect(nameInput).toHaveValue("Production");
		expect(secretInput).toHaveValue("raw-secret-value");
		expect(
			within(createDialog).getByRole("button", { name: /create secret/i }),
		).toBeEnabled();
	});

	it("does not report copy success after the dialog closes mid-copy", async () => {
		let resolveCopy!: (value: boolean) => void;
		mockAuthFetch.mockResolvedValueOnce(makeResponse([]));
		mockCopyToClipboard.mockImplementationOnce(
			() =>
				new Promise<boolean>((resolve) => {
					resolveCopy = resolve;
				}),
		);

		const view = renderDialog();

		await screen.findByText(/no embed secrets configured/i);
		await view.user.click(screen.getByRole("tab", { name: /integration guide/i }));
		await view.user.click(screen.getByRole("button", { name: /copy embed snippet/i }));

		view.unmount();
		resolveCopy(true);

		await waitFor(() => {
			expect(mockCopyToClipboard).toHaveBeenCalledTimes(1);
		});
		expect(mockToast.success).not.toHaveBeenCalledWith("Copied embed snippet");
	});

	it("copies the embed snippet with success and failure feedback", async () => {
		mockAuthFetch.mockResolvedValueOnce(makeResponse([]));
		mockCopyToClipboard
			.mockResolvedValueOnce(true)
			.mockResolvedValueOnce(false);

		const { user } = renderDialog();

		await screen.findByText(/no embed secrets configured/i);
		await user.click(
			screen.getByRole("tab", { name: /integration guide/i }),
		);
		await user.click(screen.getByRole("button", { name: /copy embed snippet/i }));

		await waitFor(() => {
			expect(mockCopyToClipboard).toHaveBeenCalledWith(
				expect.stringContaining("<iframe"),
			);
		});
		expect(mockToast.success).toHaveBeenCalledWith("Copied embed snippet");
		expect(
			screen.getByRole("button", { name: /copy embed snippet/i }),
		).toHaveTextContent("");

		await user.click(screen.getByRole("button", { name: /copy embed snippet/i }));

		await waitFor(() => {
			expect(mockToast.error).toHaveBeenCalledWith(
				"Failed to copy embed snippet",
			);
		});
	});

	it("deletes a secret and refreshes the list", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(
				makeResponse([
					{
						id: "secret-1",
						name: "Production",
						is_active: true,
						hmac_scheme: "shopify",
						created_at: "2026-09-07T12:00:00.000Z",
					},
				]),
			)
			.mockResolvedValueOnce(makeResponse({}))
			.mockResolvedValueOnce(makeResponse([]));

		const { user } = renderDialog();

		expect(await screen.findByText("Production")).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: /delete production/i }));

		const deleteDialog = await screen.findByRole("alertdialog");
		expect(within(deleteDialog).getByText(/delete embed secret\?/i)).toBeInTheDocument();
		await user.click(within(deleteDialog).getByRole("button", { name: /delete/i }));

		await waitFor(() => {
			expect(screen.queryByText("Production")).not.toBeInTheDocument();
		});
		expect(mockToast.success).toHaveBeenCalledWith("Secret deleted");
	});

	it("keeps the delete confirmation visible after a failure and retries the request", async () => {
		mockAuthFetch
			.mockResolvedValueOnce(
				makeResponse([
					{
						id: "secret-1",
						name: "Production",
						is_active: true,
						hmac_scheme: "shopify",
						created_at: "2026-09-07T12:00:00.000Z",
					},
				]),
			)
			.mockRejectedValueOnce(new Error("delete failed"))
			.mockResolvedValueOnce(makeResponse({}))
			.mockResolvedValueOnce(makeResponse([]));

		const { user } = renderDialog();

		expect(await screen.findByText("Production")).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: /delete production/i }));
		expect(screen.getByText(/delete embed secret\?/i)).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /delete/i }));

		await waitFor(() => {
			expect(mockToast.error).toHaveBeenCalledWith("Failed to delete secret");
		});
		expect(screen.getByText(/delete embed secret\?/i)).toBeInTheDocument();
		expect(screen.getByRole("alert")).toHaveTextContent("delete failed");
		expect(screen.getByRole("button", { name: /retry delete/i })).toBeInTheDocument();
		expect(
			mockAuthFetch.mock.calls.filter(
				([url, init]) =>
					url === "/api/applications/app-1/embed-secrets/secret-1" &&
					(init as RequestInit | undefined)?.method === "DELETE",
			),
		).toHaveLength(1);

		await user.click(screen.getByRole("button", { name: /retry delete/i }));

		await waitFor(() => {
			expect(screen.queryByText(/delete embed secret\?/i)).not.toBeInTheDocument();
		});
		expect(
			mockAuthFetch.mock.calls.filter(
				([url, init]) =>
					url === "/api/applications/app-1/embed-secrets/secret-1" &&
					(init as RequestInit | undefined)?.method === "DELETE",
			),
		).toHaveLength(2);
		expect(mockToast.success).toHaveBeenCalledWith("Secret deleted");
	});

	it("prevents duplicate toggle mutations while an update is pending", async () => {
		let resolveToggle!: (value: Response) => void;
		mockAuthFetch
			.mockResolvedValueOnce(
				makeResponse([
					{
						id: "secret-1",
						name: "Production",
						is_active: true,
						hmac_scheme: "shopify",
						created_at: "2026-09-07T12:00:00.000Z",
					},
				]),
			)
			.mockImplementationOnce(
				() =>
					new Promise<Response>((resolve) => {
						resolveToggle = resolve;
					}),
			)
			.mockResolvedValueOnce(makeResponse([]));

		const { user } = renderDialog();

		expect(await screen.findByText("Production")).toBeInTheDocument();
		const toggleButton = screen.getByRole("button", { name: "Deactivate" });
		await user.click(toggleButton);
		expect(toggleButton).toBeDisabled();

		await user.click(toggleButton);
		expect(
			mockAuthFetch.mock.calls.filter(
				([url, init]) =>
					url === "/api/applications/app-1/embed-secrets/secret-1" &&
					(init as RequestInit | undefined)?.method === "PATCH",
			),
		).toHaveLength(1);

		resolveToggle(makeResponse({}));
		await waitFor(() =>
			expect(mockToast.success).toHaveBeenCalledWith("Secret deactivated"),
		);
	});

	it("prevents duplicate create mutations while a create is pending", async () => {
		let resolveCreate!: (value: Response) => void;
		mockAuthFetch
			.mockResolvedValueOnce(makeResponse([]))
			.mockImplementationOnce(
				() =>
					new Promise<Response>((resolve) => {
						resolveCreate = resolve;
					}),
			)
			.mockResolvedValueOnce(makeResponse([]));

		const { user } = renderDialog();

		await screen.findByText(/no embed secrets configured/i);
		await user.click(screen.getByRole("button", { name: /create secret/i }));

		const createDialog = await screen.findByRole("dialog", {
			name: /create embed secret/i,
		});
		await user.type(within(createDialog).getByLabelText(/^name$/i), "Production");

		const submitButton = within(createDialog).getByRole("button", {
			name: /create secret/i,
		});
		expect(submitButton).toBeEnabled();

		await user.click(submitButton);
		await user.click(submitButton);

		expect(
			mockAuthFetch.mock.calls.filter(
				([url, init]) =>
					url === "/api/applications/app-1/embed-secrets" &&
					(init as RequestInit | undefined)?.method === "POST",
			),
		).toHaveLength(1);
		expect(submitButton).toBeDisabled();

		resolveCreate(makeResponse({
			id: "secret-1",
			name: "Production",
			is_active: true,
			hmac_scheme: "shopify",
			created_at: "2026-09-07T12:00:00.000Z",
			raw_secret: "raw-secret-value",
		}));
		await waitFor(() =>
			expect(mockToast.success).toHaveBeenCalledWith("Embed secret created"),
		);
	});

});
