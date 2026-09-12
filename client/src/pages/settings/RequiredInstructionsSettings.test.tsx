import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getSettings = vi.fn();
const updateSettings = vi.fn();

vi.mock("@/services/required-instructions", () => ({
	getRequiredInstructionsSettings: (organizationId?: string) =>
		getSettings(organizationId),
	updateRequiredInstructionsSettings: (
		instructions: string,
		organizationId?: string,
	) => updateSettings(instructions, organizationId),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/components/ui/tiptap-editor", () => ({
	TiptapEditor: ({
		content,
		onChange,
		ariaLabel,
	}: {
		content: string;
		onChange: (value: string) => void;
		ariaLabel: string;
	}) => (
		<textarea
			aria-label={ariaLabel}
			value={content}
			onChange={(event) => onChange(event.target.value)}
		/>
	),
}));

import { RequiredInstructionsSettings } from "./RequiredInstructionsSettings";

describe("RequiredInstructionsSettings", () => {
	beforeEach(() => {
		getSettings.mockReset().mockResolvedValue({ instructions: "" });
		updateSettings.mockReset().mockImplementation((instructions) =>
			Promise.resolve({ instructions }),
		);
	});

	it("edits global required instructions", async () => {
		const user = userEvent.setup();
		render(<RequiredInstructionsSettings />);

		const editor = await screen.findByRole("textbox", {
			name: "Global Instructions editor",
		});
		await user.type(editor, "Always verify the customer.");
		await user.click(
			screen.getByRole("button", { name: "Save Instructions" }),
		);

		await waitFor(() =>
			expect(updateSettings).toHaveBeenCalledWith(
				"Always verify the customer.",
				undefined,
			),
		);
	});

	it("loads and saves an organization-specific scope", async () => {
		getSettings.mockResolvedValue({ instructions: "Use Acme's runbook." });
		const user = userEvent.setup();
		render(
			<RequiredInstructionsSettings organizationId="org-1" embedded />,
		);

		const editor = await screen.findByRole("textbox", {
			name: "Organization Instructions editor",
		});
		await user.type(editor, " Confirm approval.");
		await user.click(
			screen.getByRole("button", { name: "Save Instructions" }),
		);

		await waitFor(() =>
			expect(updateSettings).toHaveBeenCalledWith(
				"Use Acme's runbook. Confirm approval.",
				"org-1",
			),
		);
	});
	it("retries a failed read before exposing an editable form", async () => {
		getSettings.mockRejectedValueOnce(new Error("Synthetic failure"));
		const user = userEvent.setup();
		render(<RequiredInstructionsSettings />);
		expect(await screen.findByRole("alert")).toHaveTextContent("Retry before editing");
		expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Save Instructions" })).toBeDisabled();
		await user.click(screen.getByRole("button", { name: "Retry instructions" }));
		expect(await screen.findByRole("textbox")).toBeVisible();
	});

	it("clears the previous scope while a new organization loads", async () => {
		getSettings.mockResolvedValueOnce({ instructions: "First organization" }).mockReturnValueOnce(new Promise(() => {}));
		const { rerender } = render(<RequiredInstructionsSettings organizationId="first" />);
		expect(await screen.findByRole("textbox")).toHaveValue("First organization");
		rerender(<RequiredInstructionsSettings organizationId="second" />);
		expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
		expect(screen.getByRole("status")).toBeVisible();
		expect(screen.getByRole("button", { name: "Save Instructions" })).toBeDisabled();
	});

	it("retains draft text on a failed save", async () => {
		updateSettings.mockRejectedValueOnce(new Error("Synthetic failure"));
		const user = userEvent.setup();
		render(<RequiredInstructionsSettings />);
		const input = await screen.findByRole("textbox");
		await user.type(input, "Keep this draft");
		await user.click(screen.getByRole("button", { name: "Save Instructions" }));
		expect(await screen.findByRole("alert")).toHaveTextContent("Your draft is preserved");
		expect(input).toHaveValue("Keep this draft");
	});

});
