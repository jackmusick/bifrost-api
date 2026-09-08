import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SourceControlActions } from "./SourceControlActions";
const props = () => ({
	hasChanges: true,
	hasConflicts: false,
	allConflictsResolved: false,
	commitMessage: "Update workflow",
	onCommitMessageChange: vi.fn(),
	onCommit: vi.fn(),
	onCompleteMerge: vi.fn(),
	onSync: vi.fn(),
	commitsAhead: 2,
	commitsBehind: 1,
	needsSync: true,
	disabled: false,
	loading: null,
	branch: "feature/review",
});
it("supports Enter commit and explains why sync is disabled", async () => {
	const user = userEvent.setup();
	const p = props();
	const { rerender } = render(<SourceControlActions {...p} />);
	await user.click(screen.getByLabelText("Commit message"));
	await user.keyboard("{Enter}");
	expect(p.onCommit).toHaveBeenCalledTimes(1);
	expect(screen.getByRole("button", { name: "Sync origin" })).toBeDisabled();
	expect(screen.getByText("2 outgoing · 1 incoming")).toBeVisible();
	rerender(<SourceControlActions {...p} disabled />);
	expect(screen.getByLabelText("Commit message")).toBeDisabled();
	expect(
		screen.getByRole("button", { name: "Commit changes" }),
	).toBeDisabled();
});
it("keeps normal commit controls out of conflict mode and gates merge completion", async () => {
	const user = userEvent.setup();
	const p = props();
	const { rerender } = render(<SourceControlActions {...p} hasConflicts />);
	expect(screen.queryByLabelText("Commit message")).not.toBeInTheDocument();
	expect(
		screen.getByRole("button", { name: "Complete merge" }),
	).toBeDisabled();
	rerender(<SourceControlActions {...p} hasConflicts allConflictsResolved />);
	await user.click(screen.getByRole("button", { name: "Complete merge" }));
	expect(p.onCompleteMerge).toHaveBeenCalledTimes(1);
	expect(p.onCommit).not.toHaveBeenCalled();
});
