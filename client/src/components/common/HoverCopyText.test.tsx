import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { HoverCopyText } from "./HoverCopyText";

const mockCopyToClipboard = vi.fn();

vi.mock("@/lib/clipboard", () => ({
	copyToClipboard: (value: string) => mockCopyToClipboard(value),
}));

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

beforeEach(() => {
	mockCopyToClipboard.mockReset();
	mockCopyToClipboard.mockResolvedValue(true);
});

describe("HoverCopyText", () => {
	it("shows the portal copy action on hover and copies the value on click", async () => {
		const user = userEvent.setup();
		render(<HoverCopyText value="doc-123" label="Document ID" />);

		await user.hover(
			screen.getByRole("button", { name: "Copy Document ID" }),
		);
		expect(await screen.findByText("Copy")).toBeVisible();

		await user.click(
			screen.getByRole("button", { name: "Copy Document ID" }),
		);
		expect(mockCopyToClipboard).toHaveBeenCalledWith("doc-123");
		expect(await screen.findByText("Copied")).toBeVisible();
		expect(
			screen.getByRole("button", { name: "Document ID copied" }),
		).toBeVisible();
	});

	it("opens for keyboard focus and closes on blur", async () => {
		const user = userEvent.setup();
		render(
			<>
				<HoverCopyText value="doc-123" label="Document ID" />
				<button type="button">Next</button>
			</>,
		);

		await user.tab();
		expect(await screen.findByText("Copy")).toBeVisible();

		await user.tab();
		await waitFor(() => expect(screen.queryByText("Copy")).toBeNull());
	});
});
