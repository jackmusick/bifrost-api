import { useRef, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test-utils";
import * as clipboard from "@/lib/clipboard";
import {
	WorkflowKeyCreateDialog,
	WorkflowKeyRevealDialog,
	WorkflowKeyRevokeDialog,
} from "./WorkflowKeyDialogs";

const toastApi = vi.hoisted(() => ({
	success: vi.fn(),
	error: vi.fn(),
}));

vi.mock("@/lib/clipboard", () => ({
	copyToClipboard: vi.fn(),
}));

vi.mock("sonner", () => ({
	toast: toastApi,
}));

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

describe("WorkflowKey dialogs", () => {
	it("returns focus to the create opener when the dialog is canceled", async () => {
		const user = userEvent.setup();

		function Harness() {
			const openerRef = useRef<HTMLButtonElement>(null);
			const [open, setOpen] = useState(false);

			return (
				<>
					<button type="button" ref={openerRef} onClick={() => setOpen(true)}>
						Open create dialog
					</button>
					<WorkflowKeyCreateDialog
						open={open}
						onOpenChange={setOpen}
						onSubmit={vi.fn()}
						pending={false}
						error={null}
						canSubmit
						workflowOptions={[
							{ value: "workflow-1", label: "Workflow One" },
						]}
						returnFocusRef={openerRef}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open create dialog/i }));
		await user.click(screen.getByRole("button", { name: /^cancel$/i }));

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /open create dialog/i }),
			).toHaveFocus();
		});
	});

	it("shows copy failure inline and succeeds on retry in the reveal dialog", async () => {
		const user = userEvent.setup();
		const copySpy = vi
			.spyOn(clipboard, "copyToClipboard")
			.mockResolvedValueOnce(false)
			.mockResolvedValueOnce(true);

		function Harness() {
			const openerRef = useRef<HTMLButtonElement>(null);
			const [open, setOpen] = useState(false);

			return (
				<>
					<button type="button" ref={openerRef} onClick={() => setOpen(true)}>
						Open reveal dialog
					</button>
					<WorkflowKeyRevealDialog
						open={open}
						onOpenChange={setOpen}
						rawKey="raw-secret-key"
						description="CRM integration"
						scopeLabel="Global"
						workflowId="workflow-1"
						expiresLabel="Never"
						returnFocusRef={openerRef}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open reveal dialog/i }));
		await user.click(screen.getByRole("button", { name: /copy api key/i }));

		expect(
			await screen.findByText(/could not copy the api key/i),
		).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /copy api key/i }));
		await waitFor(() => expect(copySpy).toHaveBeenCalledTimes(2));
		expect(toastApi.success).toHaveBeenCalledWith(
			"API key copied to clipboard",
		);
		expect(
			screen.getByRole("button", { name: /copied api key/i }),
		).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /i'?ve copied the key/i }));
		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /open reveal dialog/i }),
			).toHaveFocus();
		});
	});

	it("keeps the revoke dialog open on confirm and returns focus to the trigger on cancel", async () => {
		const user = userEvent.setup();
		const onConfirm = vi.fn();

		function Harness() {
			const triggerRef = useRef<HTMLButtonElement>(null);
			const [open, setOpen] = useState(false);

			return (
				<>
					<button type="button" ref={triggerRef} onClick={() => setOpen(true)}>
						Open revoke dialog
					</button>
					<WorkflowKeyRevokeDialog
						open={open}
						onOpenChange={(next) => setOpen(next)}
						keyLabel="abcd1234"
						error={null}
						pending={false}
						returnFocusRef={triggerRef}
						preferFallback={false}
						onConfirm={onConfirm}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open revoke dialog/i }));
		await user.click(screen.getByRole("button", { name: /^cancel$/i }));

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /open revoke dialog/i }),
			).toHaveFocus();
		});

		await user.click(screen.getByRole("button", { name: /open revoke dialog/i }));
		await user.click(screen.getByRole("button", { name: /revoke key/i }));

		expect(onConfirm).toHaveBeenCalledTimes(1);
		expect(
			screen.getByRole("button", { name: /revoke key/i }),
		).toBeInTheDocument();
	});

	it("returns focus to the heading after a successful revoke", async () => {
		const user = userEvent.setup();

		function Harness() {
			const triggerRef = useRef<HTMLButtonElement>(null);
			const headingRef = useRef<HTMLHeadingElement>(null);
			const [open, setOpen] = useState(false);
			const [preferFallback, setPreferFallback] = useState(false);

			return (
				<>
					<button type="button" ref={triggerRef} onClick={() => setOpen(true)}>
						Open revoke dialog
					</button>
					<h2 ref={headingRef} tabIndex={-1}>
						Workflow Keys
					</h2>
					<WorkflowKeyRevokeDialog
						open={open}
						onOpenChange={(next) => setOpen(next)}
						keyLabel="abcd1234"
						error={null}
						pending={false}
						returnFocusRef={triggerRef}
						preferFallback={preferFallback}
						fallbackRef={headingRef}
						onConfirm={() => {
							setPreferFallback(true);
							setOpen(false);
						}}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open revoke dialog/i }));
		await user.click(screen.getByRole("button", { name: /revoke key/i }));

		await waitFor(() => {
			expect(screen.getByRole("heading", { name: /workflow keys/i })).toHaveFocus();
		});
	});
});
