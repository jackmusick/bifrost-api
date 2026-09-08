import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { it, expect, vi } from "vitest";
import {
	ChangedFileRecord,
	ConflictFileRecord,
} from "./SourceControlFileRecords";
const file = {
	path: "workflows/long_workflow.py",
	display_name: "Customer workflow",
	entity_type: "workflow",
	change_type: "modified" as const,
};
it("keeps diff and discard actions separate and keyboard accessible", async () => {
	const user = userEvent.setup();
	const onShowDiff = vi.fn(),
		onDiscard = vi.fn();
	render(
		<ChangedFileRecord
			file={file}
			onShowDiff={onShowDiff}
			onDiscard={onDiscard}
		/>,
	);
	expect(screen.getByText(file.path)).toBeVisible();
	const diff = screen.getByRole("button", {
		name: `View changes for ${file.path}`,
	});
	diff.focus();
	await user.keyboard("{Enter}");
	expect(onShowDiff).toHaveBeenCalledTimes(1);
	await user.click(
		screen.getByRole("button", { name: `Discard changes to ${file.path}` }),
	);
	expect(onDiscard).toHaveBeenCalledTimes(1);
	expect(onShowDiff).toHaveBeenCalledTimes(1);
});
it("exposes conflict selection and blocks changes while the host is busy", async () => {
	const user = userEvent.setup();
	const onResolve = vi.fn();
	const props = { conflict: file, onShowDiff: vi.fn(), onResolve };
	const { rerender } = render(<ConflictFileRecord {...props} />);
	await user.click(screen.getByRole("button", { name: "Keep local" }));
	expect(onResolve).toHaveBeenCalledWith("ours");
	rerender(<ConflictFileRecord {...props} resolution="ours" disabled />);
	expect(screen.getByRole("button", { name: "Keep local" })).toHaveAttribute(
		"aria-pressed",
		"true",
	);
	expect(screen.getByText("Local version selected")).toBeVisible();
	expect(screen.getByRole("button", { name: "Keep remote" })).toBeDisabled();
});
