import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
	status: vi.fn(),
	setup: vi.fn(),
	refetch: vi.fn(),
	passkeyList: vi.fn(),
	register: vi.fn(),
	delete: vi.fn(),
}));

vi.mock("@/hooks/usePasskeys", () => ({
	usePasskeySupport: () => ({ supported: true, isLoading: false }),
	usePasskeyList: (...args: unknown[]) => mocks.passkeyList(...args),
	useRegisterPasskey: () => ({
		mutate: mocks.register,
		isPending: false,
	}),
	useDeletePasskey: () => ({
		mutate: mocks.delete,
		isPending: false,
	}),
}));

vi.mock("@/services/mfa", () => ({
	mfaService: { getMFAStatus: mocks.status, setupTOTP: mocks.setup },
}));

import { Security } from "./Security";

beforeEach(() => {
	vi.clearAllMocks();
	mocks.passkeyList.mockReturnValue({
		data: {
			passkeys: [
				{
					id: "one",
					name: "Saved laptop",
					device_type: "singleDevice",
					created_at: "2026-09-07T00:00:00Z",
					last_used_at: null,
				},
			],
			count: 1,
		},
		isError: true,
		isLoading: false,
		isFetching: false,
		refetch: mocks.refetch,
	});
	mocks.status.mockResolvedValue({
		mfa_enabled: false,
		enrolled_methods: [],
		recovery_codes_remaining: 0,
	});
	mocks.register.mockImplementation((_deviceName, options) => {
		options?.onSuccess?.({ passkey_id: "two", name: "Work laptop" });
	});
	mocks.delete.mockImplementation((_passkeyId, options) => {
		options?.onSuccess?.();
	});
});

it("retains cached passkeys and retries failed authentication reads", async () => {
	mocks.status.mockRejectedValueOnce(new Error("Offline"));
	const user = userEvent.setup();
	render(<Security />);
	expect(await screen.findByText("Saved laptop")).toBeVisible();
	await user.click(
		await screen.findByRole("button", {
			name: "Retry authentication status",
		}),
	);
	await screen.findByRole("button", { name: "Set Up" });
	expect(mocks.status).toHaveBeenCalledTimes(2);
	await user.click(screen.getByRole("button", { name: "Retry passkeys" }));
	expect(mocks.refetch).toHaveBeenCalledTimes(1);
});

it("keeps a failed setup visible with focused retry feedback", async () => {
	mocks.setup.mockRejectedValue(new Error("Setup unavailable"));
	const user = userEvent.setup();
	render(<Security />);
	await user.click(await screen.findByRole("button", { name: "Set Up" }));
	const error = await screen.findByText("Setup unavailable");
	await waitFor(() => expect(error.closest('[role="alert"]')).toHaveFocus());
	await user.click(
		screen.getByRole("button", { name: "Retry authenticator setup" }),
	);
	expect(mocks.setup).toHaveBeenCalledTimes(2);
});

it("wires the extracted passkey dialogs through add, delete, and focus fallback", async () => {
	const user = userEvent.setup();
	render(<Security />);

	await user.click(screen.getByRole("button", { name: "Add Passkey" }));
	await user.type(screen.getByLabelText(/device name/i), "Work laptop");
	await user.click(screen.getByRole("button", { name: "Register Passkey" }));

	await waitFor(() => {
		expect(mocks.register).toHaveBeenCalledWith(
			"Work laptop",
			expect.objectContaining({ onSuccess: expect.any(Function) }),
		);
		expect(
			screen.getByRole("button", { name: "Add Passkey" }),
		).toBeVisible();
	});

	await user.click(screen.getByRole("button", { name: "Add Passkey" }));
	expect(screen.getByLabelText(/device name/i)).toHaveValue("");
	await user.click(screen.getByRole("button", { name: "Cancel" }));

	await user.click(
		screen.getByRole("button", { name: /remove passkey saved laptop/i }),
	);
	await user.click(screen.getByRole("button", { name: "Remove Passkey" }));

	await waitFor(() => {
		expect(mocks.delete).toHaveBeenCalledWith(
			"one",
			expect.objectContaining({ onSuccess: expect.any(Function) }),
		);
		expect(screen.getByRole("heading", { name: "Passkeys" })).toHaveFocus();
	});
});
