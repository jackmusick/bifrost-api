import { useRef, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test-utils";
import { SecurityMfaDialogs } from "./SecurityMfaDialogs";

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

describe("SecurityMfaDialogs", () => {
	it("locks the remove dialog while pending and focuses persistent errors", async () => {
		const onRemove = vi.fn();
		const onRemoveOpenChange = vi.fn();
		const user = userEvent.setup();
		const passcode = "123456";

		renderWithProviders(
			<SecurityMfaDialogs
				removeOpen
				onRemoveOpenChange={onRemoveOpenChange}
				removeCode={passcode}
				onRemoveCodeChange={vi.fn()}
				onRemove={onRemove}
				isRemoving
				removeError="Synthetic remove failure"
				regenerateOpen={false}
				onRegenerateOpenChange={vi.fn()}
				regenerateCode=""
				onRegenerateCodeChange={vi.fn()}
				onRegenerate={vi.fn()}
				isRegenerating={false}
				regenerateError={null}
			/>,
		);

		expect(screen.getByLabelText(/authenticator code/i)).toBeDisabled();
		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByRole("button", { name: /remove mfa/i })).toBeDisabled();
		const error = screen
			.getByText(/synthetic remove failure/i)
			.closest('[role="alert"]') as HTMLElement | null;
		expect(error).not.toBeNull();
		await waitFor(() => expect(error).toHaveFocus());

		await user.keyboard("{Escape}");
		expect(onRemoveOpenChange).not.toHaveBeenCalled();
		expect(onRemove).not.toHaveBeenCalled();
	});

	it("returns focus to the opener on cancel and falls back to the MFA heading after success", async () => {
		const user = userEvent.setup();

		function Harness() {
			const openerRef = useRef<HTMLButtonElement>(null);
			const headingRef = useRef<HTMLHeadingElement>(null);
			const [open, setOpen] = useState(false);
			const [preferFallback, setPreferFallback] = useState(false);

			return (
				<>
					<button type="button" ref={openerRef} onClick={() => setOpen(true)}>
						Open remove dialog
					</button>
					<h2 ref={headingRef} tabIndex={-1}>
						Two-Factor Authentication
					</h2>
					<SecurityMfaDialogs
						removeOpen={open}
						onRemoveOpenChange={(nextOpen) => {
							if (nextOpen) {
								setPreferFallback(false);
							}
							setOpen(nextOpen);
						}}
						removeCode="123456"
						onRemoveCodeChange={vi.fn()}
						onRemove={() => {
							setPreferFallback(true);
							setOpen(false);
						}}
						isRemoving={false}
						removeError={null}
						removePreferFallback={preferFallback}
						removeReturnFocusRef={openerRef}
						removeFallbackRef={headingRef}
						regenerateOpen={false}
						onRegenerateOpenChange={vi.fn()}
						regenerateCode=""
						onRegenerateCodeChange={vi.fn()}
						onRegenerate={vi.fn()}
						isRegenerating={false}
						regenerateError={null}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open remove dialog/i }));
		await user.click(screen.getByRole("button", { name: /cancel/i }));

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /open remove dialog/i })).toHaveFocus();
		});

		await user.click(screen.getByRole("button", { name: /open remove dialog/i }));
		await user.click(screen.getByRole("button", { name: /remove mfa/i }));

		await waitFor(() => {
			expect(screen.getByRole("heading", { name: /two-factor authentication/i })).toHaveFocus();
		});
	});

	it("keeps the regenerate dialog open while pending and focuses errors", async () => {
		const onRegenerate = vi.fn();
		const onRegenerateOpenChange = vi.fn();
		const user = userEvent.setup();

		renderWithProviders(
			<SecurityMfaDialogs
				removeOpen={false}
				onRemoveOpenChange={vi.fn()}
				removeCode=""
				onRemoveCodeChange={vi.fn()}
				onRemove={vi.fn()}
				isRemoving={false}
				removeError={null}
				regenerateOpen
				onRegenerateOpenChange={onRegenerateOpenChange}
				regenerateCode="654321"
				onRegenerateCodeChange={vi.fn()}
				onRegenerate={onRegenerate}
				isRegenerating
				regenerateError="Synthetic regenerate failure"
			/>,
		);

		const error = screen
			.getByText(/synthetic regenerate failure/i)
			.closest('[role="alert"]') as HTMLElement | null;
		expect(error).not.toBeNull();
		await waitFor(() => expect(error).toHaveFocus());
		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByRole("button", { name: /regenerate\.\.\./i })).toBeDisabled();

		await user.keyboard("{Escape}");
		expect(onRegenerateOpenChange).not.toHaveBeenCalled();
		expect(onRegenerate).not.toHaveBeenCalled();
	});
});
