import { useRef, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test-utils";
import { PricingDeleteDialog } from "./PricingDeleteDialog";

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

const pricing = {
	id: 1,
	model: "gpt-4.1",
	provider: "openai",
	input_price_per_million: "5.00",
	output_price_per_million: "15.00",
	effective_date: "2026-09-01",
	created_at: "2026-09-01T00:00:00Z",
	updated_at: "2026-09-01T00:00:00Z",
	cache_read_price_per_million: null,
	cache_write_price_per_million: null,
	is_used: true,
} as const;

describe("PricingDeleteDialog", () => {
	it("locks the dialog while pending and focuses persistent errors", async () => {
		const onClose = vi.fn();
		const onConfirm = vi.fn();
		const user = userEvent.setup();

		renderWithProviders(
			<PricingDeleteDialog
				pricing={pricing}
				pending
				failed
				onClose={onClose}
				onConfirm={onConfirm}
			/>,
		);

		expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
		expect(screen.getByRole("button", { name: /deleting/i })).toBeDisabled();
		const error = screen.getByRole("alert");
		await waitFor(() => expect(error).toHaveFocus());

		await user.keyboard("{Escape}");
		expect(onClose).not.toHaveBeenCalled();
		expect(onConfirm).not.toHaveBeenCalled();
	});

	it("returns focus to the opener on cancel and to the fallback heading after success", async () => {
		const user = userEvent.setup();

		function Harness() {
			const fallbackRef = useRef<HTMLHeadingElement>(null);
			const [open, setOpen] = useState(false);
			const [completed, setCompleted] = useState(false);

			return (
				<>
					<button type="button" onClick={() => setOpen(true)}>
						Open delete dialog
					</button>
					<h2 ref={fallbackRef} tabIndex={-1}>
						Model pricing
					</h2>
					<PricingDeleteDialog
						pricing={open ? pricing : null}
						pending={false}
						failed={false}
						completed={completed}
						returnFocusRef={fallbackRef}
						onClose={() => setOpen(false)}
						onConfirm={() => {
							setCompleted(true);
							setOpen(false);
						}}
					/>
				</>
			);
		}

		renderWithProviders(<Harness />);

		await user.click(screen.getByRole("button", { name: /open delete dialog/i }));
		await user.click(screen.getByRole("button", { name: /cancel/i }));

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /open delete dialog/i })).toHaveFocus();
		});

		await user.click(screen.getByRole("button", { name: /open delete dialog/i }));
		await user.click(screen.getByRole("button", { name: /delete pricing/i }));

		await waitFor(() => {
			expect(screen.getByRole("heading", { name: /model pricing/i })).toHaveFocus();
		});
	});
});
