import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SourceDiscardDialog } from "./SourceDiscardDialog";

it("retains reviewed files after failure, guards pending dismissal and closes only after success", async () => {
	const user = userEvent.setup();
	const files = [
		{
			path: "workflows/a_long_folder/workflow.py",
			change_type: "modified" as const,
		},
	];
	let reject!: (reason: Error) => void;
	const onConfirm = vi
		.fn()
		.mockImplementationOnce(
			() =>
				new Promise<void>((_, fail) => {
					reject = fail;
				}),
		)
		.mockResolvedValue(undefined);
	const onClose = vi.fn();
	render(
		<SourceDiscardDialog
			files={files}
			onClose={onClose}
			onConfirm={onConfirm}
		/>,
	);
	expect(screen.getByRole("alertdialog")).toHaveAccessibleDescription("Discard uncommitted changes to this file. This cannot be undone.");
	await user.click(screen.getByRole("button", { name: "Discard changes" }));
	expect(onConfirm).toHaveBeenCalledWith(files);
	expect(screen.getByRole("button", { name: "Keep changes" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
	await act(async () => reject(new Error("Repository unavailable")));
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Repository unavailable",
	);
	expect(screen.getByText(files[0].path)).toBeVisible();
	await user.click(screen.getByRole("button", { name: "Discard changes" }));
	expect(onConfirm).toHaveBeenCalledTimes(2);
	expect(onClose).toHaveBeenCalledTimes(1);
});
