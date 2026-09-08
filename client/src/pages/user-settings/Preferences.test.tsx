import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getSettings = vi.fn();
const updateSettings = vi.fn();
const getMemories = vi.fn();
const deleteMemory = vi.fn();

vi.mock("@/services/memory", () => ({
	getUserMemorySettings: () => getSettings(),
	updateUserMemorySettings: (enabled: boolean) => updateSettings(enabled),
	listMemories: () => getMemories(),
	removeMemory: (memoryId: string) => deleteMemory(memoryId),
}));
vi.mock("@/components/ui/tiptap-editor", () => ({
	TiptapEditor: ({
		content,
		ariaLabel,
	}: {
		content: string;
		ariaLabel: string;
	}) => <article aria-label={ariaLabel}>{content}</article>,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { Preferences } from "./Preferences";

const settings = {
	platform_enabled: true,
	user_enabled: true,
	effective_enabled: true,
};

describe("Preferences", () => {
	beforeEach(() => {
		getSettings.mockReset().mockResolvedValue(settings);
		updateSettings.mockReset().mockResolvedValue({
			...settings,
			user_enabled: false,
			effective_enabled: false,
		});
		getMemories.mockReset().mockResolvedValue({
			count: 1,
			entries: [
				{
					id: "84c4c4cb-37d6-4fb1-9472-b266dd0e429a",
					content: "## Acme onboarding\nUse the customer checklist.",
					metadata: {},
					created_at: "2026-08-12T20:00:00Z",
					updated_at: "2026-08-12T20:00:00Z",
				},
			],
		});
		deleteMemory.mockReset().mockResolvedValue(undefined);
	});

	it("lets the user opt out and renders saved markdown through the viewer", async () => {
		const user = userEvent.setup();
		render(<Preferences />);

		const toggle = await screen.findByRole("switch", {
			name: "Enable Memory",
		});
		await waitFor(() => expect(toggle).toBeEnabled());
		expect(
			screen.getByRole("article", { name: "Saved memory" }),
		).toHaveTextContent("Acme onboarding");

		await user.click(toggle);
		await waitFor(() => expect(updateSettings).toHaveBeenCalledWith(false));
	});

	it("shows a retryable save error when updating the memory toggle fails", async () => {
		updateSettings.mockRejectedValueOnce(new Error("Offline"));
		const user = userEvent.setup();
		render(<Preferences />);

		const toggle = await screen.findByRole("switch", {
			name: "Enable Memory",
		});
		await user.click(toggle);

		expect(
			await screen.findByText(
				/Offline\. Your memory preference is still ready to retry\./,
			),
		).toBeVisible();
		expect(updateSettings).toHaveBeenCalledWith(false);

		await user.click(screen.getByRole("button", { name: "Retry save" }));
		await waitFor(() => expect(updateSettings).toHaveBeenCalledTimes(2));
		expect(updateSettings).toHaveBeenLastCalledWith(false);
	});

	it("ignores duplicate toggle submits while the preference save is pending", async () => {
		let resolveUpdate!: (value: unknown) => void;
		updateSettings.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					resolveUpdate = resolve;
				}),
		);
		render(<Preferences />);

		const toggle = await screen.findByRole("switch", {
			name: "Enable Memory",
		});
		fireEvent.click(toggle);
		fireEvent.click(toggle);

		expect(updateSettings).toHaveBeenCalledTimes(1);
		resolveUpdate({
			...settings,
			user_enabled: false,
			effective_enabled: false,
		});
		await waitFor(() => expect(toggle).toBeEnabled());
	});

	it("confirms before removing a saved memory", async () => {
		const user = userEvent.setup();
		render(<Preferences />);

		await user.click(
			await screen.findByRole("button", { name: "Remove memory" }),
		);
		await user.click(screen.getByRole("button", { name: /^Remove$/ }));

		await waitFor(() =>
			expect(deleteMemory).toHaveBeenCalledWith(
				"84c4c4cb-37d6-4fb1-9472-b266dd0e429a",
			),
		);
		expect(screen.queryByText(/Acme onboarding/)).not.toBeInTheDocument();
	});
	it("keeps controls disabled after a failed load and recovers with retry", async () => {
		getSettings.mockRejectedValueOnce(new Error("Offline"));
		const user = userEvent.setup();
		render(<Preferences />);
		await screen.findByRole("alert");
		expect(
			screen.getByRole("switch", { name: "Enable Memory" }),
		).toBeDisabled();
		expect(
			screen.queryByText("Nothing has been remembered yet."),
		).not.toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Retry" }));
		await waitFor(() =>
			expect(
				screen.getByRole("switch", { name: "Enable Memory" }),
			).toBeEnabled(),
		);
		expect(
			screen.getByRole("article", { name: "Saved memory" }),
		).toBeVisible();
	});
	it("retains the delete dialog during failure and retries the same memory", async () => {
		let rejectDelete!: (error: Error) => void;
		deleteMemory.mockImplementationOnce(
			() =>
				new Promise((_, reject) => {
					rejectDelete = reject;
				}),
		);
		const user = userEvent.setup();
		render(<Preferences />);
		await user.click(
			await screen.findByRole("button", { name: "Remove memory" }),
		);
		await user.click(screen.getByRole("button", { name: /^Remove$/ }));
		expect(
			screen.getByRole("button", { name: "Removing…" }),
		).toBeDisabled();
		await user.keyboard("{Escape}");
		expect(screen.getByRole("alertdialog")).toBeVisible();
		rejectDelete(new Error("Offline"));
		await user.click(
			await screen.findByRole("button", { name: "Retry removal" }),
		);
		await waitFor(() =>
			expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
		);
		expect(deleteMemory).toHaveBeenCalledTimes(2);
		expect(deleteMemory.mock.calls[0]).toEqual(deleteMemory.mock.calls[1]);
	});

	it("prevents duplicate delete submits and restores focus after removal", async () => {
		let resolveDelete!: (value: undefined) => void;
		deleteMemory.mockImplementationOnce(
			() =>
				new Promise<undefined>((resolve) => {
					resolveDelete = resolve;
				}),
		);
		const user = userEvent.setup();
		render(<Preferences />);

		await user.click(
			await screen.findByRole("button", { name: "Remove memory" }),
		);
		const removeButton = screen.getByRole("button", { name: "Remove" });
		fireEvent.click(removeButton);
		fireEvent.click(removeButton);
		expect(deleteMemory).toHaveBeenCalledTimes(1);
		resolveDelete(undefined);
		await waitFor(() =>
			expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
		);
		expect(
			screen.getByText("Saved Memories").closest('[tabindex="-1"]'),
		).toHaveFocus();
	});
});
