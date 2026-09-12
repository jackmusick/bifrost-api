import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test-utils";
import { SecurityPasskeyDialogs } from "./SecurityPasskeyDialogs";

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

describe("SecurityPasskeyDialogs", () => {
	it("locks the add dialog while registering and focuses persistent errors", async () => {
		const onAddOpenChange = vi.fn();
		const onRegister = vi.fn();
		const user = userEvent.setup();

		renderWithProviders(
			<SecurityPasskeyDialogs
				addOpen
				onAddOpenChange={onAddOpenChange}
				deviceName="MacBook Pro"
				onDeviceNameChange={vi.fn()}
				onRegister={onRegister}
				isRegistering
				registerError="Synthetic register failure"
				passkeyToDelete={null}
				onDeleteOpenChange={vi.fn()}
				onDelete={vi.fn()}
				isDeleting={false}
				deleteError={null}
			/>,
		);

		expect(screen.getByLabelText(/device name/i)).toBeDisabled();
		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByRole("button", { name: /registering/i })).toBeDisabled();
		const registerError = screen
			.getByText(/synthetic register failure/i)
			.closest('[role="alert"]') as HTMLElement | null;
		expect(registerError).not.toBeNull();
		await waitFor(() =>
			expect(registerError).toHaveFocus(),
		);
		expect(registerError).toHaveTextContent(/Synthetic register failure/i);

		await user.keyboard("{Escape}");
		expect(onAddOpenChange).not.toHaveBeenCalled();
	});

	it("returns focus to the opener when the add dialog closes", async () => {
		const user = userEvent.setup();

		function Harness() {
			const [open, setOpen] = useState(false);
			return (
				<>
					<button type="button" onClick={() => setOpen(true)}>
						Open add passkey
					</button>
					<SecurityPasskeyDialogs
						addOpen={open}
						onAddOpenChange={setOpen}
						deviceName=""
						onDeviceNameChange={vi.fn()}
						onRegister={vi.fn()}
						isRegistering={false}
						registerError={null}
						passkeyToDelete={null}
						onDeleteOpenChange={vi.fn()}
						onDelete={vi.fn()}
						isDeleting={false}
						deleteError={null}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open add passkey/i }));
		await user.click(screen.getByRole("button", { name: /cancel/i }));

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /open add passkey/i })).toHaveFocus();
		});
	});

	it("keeps the delete dialog open while pending and focuses errors", async () => {
		const onDelete = vi.fn();
		const onDeleteOpenChange = vi.fn();
		const user = userEvent.setup();
		const passkey = {
			id: "passkey-1",
			name: "MacBook Pro Touch ID",
			device_type: "multiDevice",
			backed_up: true,
			created_at: "2026-09-08T12:00:00Z",
			last_used_at: null,
		};

		renderWithProviders(
			<SecurityPasskeyDialogs
				addOpen={false}
				onAddOpenChange={vi.fn()}
				deviceName=""
				onDeviceNameChange={vi.fn()}
				onRegister={vi.fn()}
				isRegistering={false}
				registerError={null}
				passkeyToDelete={passkey}
				onDeleteOpenChange={onDeleteOpenChange}
				onDelete={onDelete}
				isDeleting
				deleteError="Synthetic delete failure"
			/>,
		);

		const deleteError = screen
			.getByText(/synthetic delete failure/i)
			.closest('[role="alert"]') as HTMLElement | null;
		expect(deleteError).not.toBeNull();
		await waitFor(() => expect(deleteError).toHaveFocus());
		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByRole("button", { name: /removing/i })).toBeDisabled();

		await user.keyboard("{Escape}");
		expect(onDeleteOpenChange).not.toHaveBeenCalled();
		expect(onDelete).not.toHaveBeenCalled();
	});

	it("uses an explicit button for delete without auto-closing the dialog", async () => {
		const onDelete = vi.fn();
		const onDeleteOpenChange = vi.fn();
		const user = userEvent.setup();
		const passkey = {
			id: "passkey-1",
			name: "MacBook Pro Touch ID",
			device_type: "multiDevice",
			backed_up: true,
			created_at: "2026-09-08T12:00:00Z",
			last_used_at: null,
		};

		renderWithProviders(
			<SecurityPasskeyDialogs
				addOpen={false}
				onAddOpenChange={vi.fn()}
				deviceName=""
				onDeviceNameChange={vi.fn()}
				onRegister={vi.fn()}
				isRegistering={false}
				registerError={null}
				passkeyToDelete={passkey}
				onDeleteOpenChange={onDeleteOpenChange}
				onDelete={onDelete}
				isDeleting={false}
				deleteError={null}
			/>,
		);

		await user.click(screen.getByRole("button", { name: /remove passkey/i }));

		expect(onDelete).toHaveBeenCalledTimes(1);
		expect(onDeleteOpenChange).not.toHaveBeenCalled();
		expect(screen.getByRole("heading", { name: /remove passkey\?/i })).toBeInTheDocument();
	});
});
