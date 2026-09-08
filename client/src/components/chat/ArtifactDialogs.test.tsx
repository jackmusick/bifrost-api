import { useRef, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test-utils";
import {
	ArtifactDeleteDialog,
	ArtifactRenameDialog,
} from "./ArtifactDialogs";

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

describe("Artifact dialogs", () => {
	it("returns focus to the opener when rename is canceled", async () => {
		const user = userEvent.setup();

		function Harness() {
			const openerRef = useRef<HTMLButtonElement>(null);
			const [open, setOpen] = useState(false);

			return (
				<>
					<button type="button" ref={openerRef} onClick={() => setOpen(true)}>
						Open rename dialog
					</button>
					<ArtifactRenameDialog
						open={open}
						filename="Draft.txt"
						pending={false}
						error={null}
						onOpenChange={(next) => setOpen(next)}
						onFilenameChange={vi.fn()}
						onSubmit={vi.fn()}
						returnFocusRef={openerRef}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open rename dialog/i }));
		await user.click(screen.getByRole("button", { name: /^cancel$/i }));

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /open rename dialog/i }),
			).toHaveFocus();
		});
	});

	it("focuses rename errors and blocks dismissal while pending", async () => {
		const user = userEvent.setup();
		const onOpenChange = vi.fn();

		renderWithProviders(
			<ArtifactRenameDialog
				open
				filename="Draft.txt"
				pending
				error="Could not rename this artifact. Try again."
				onOpenChange={onOpenChange}
				onFilenameChange={vi.fn()}
				onSubmit={vi.fn()}
			/>,
		);

		const alert = await screen.findByRole("alert");
		await waitFor(() => expect(alert).toHaveFocus());
		expect(screen.getByRole("button", { name: /^cancel$/i })).toBeDisabled();

		await user.keyboard("{Escape}");
		expect(onOpenChange).not.toHaveBeenCalled();
	});

	it("returns focus to the opener on cancel and to the heading after delete success", async () => {
		const user = userEvent.setup();

		function Harness() {
			const triggerRef = useRef<HTMLButtonElement>(null);
			const headingRef = useRef<HTMLHeadingElement>(null);
			const [open, setOpen] = useState(false);
			const [preferFallback, setPreferFallback] = useState(false);

			return (
				<>
					<button type="button" ref={triggerRef} onClick={() => setOpen(true)}>
						Open delete dialog
					</button>
					<h2 ref={headingRef} tabIndex={-1}>
						Artifacts
					</h2>
					<ArtifactDeleteDialog
						open={open}
						target={{
							id: "artifact-1",
							filename: "Draft.txt",
						} as never}
						pending={false}
						error={null}
						preferFallback={preferFallback}
						fallbackRef={headingRef}
						onOpenChange={(next) => setOpen(next)}
						returnFocusRef={triggerRef}
						onConfirm={() => {
							setPreferFallback(true);
							setOpen(false);
						}}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open delete dialog/i }));
		await user.click(screen.getByRole("button", { name: /^cancel$/i }));

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /open delete dialog/i }),
			).toHaveFocus();
		});

		await user.click(screen.getByRole("button", { name: /open delete dialog/i }));
		await user.click(screen.getByRole("button", { name: /delete/i }));

		await waitFor(() => {
			expect(screen.getByRole("heading", { name: /artifacts/i })).toHaveFocus();
		});
	});
});
