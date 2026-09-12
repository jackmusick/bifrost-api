import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SyncDiffHeader, SyncDiffResolution } from "./SyncDiffControls";
import type { DiffPreviewState } from "@/stores/editorStore";
it("names deletion choices explicitly and reflects selected versions", async () => {
	const user = userEvent.setup();
	const onResolve = vi.fn();
	const onClose = vi.fn();
	const preview: DiffPreviewState = {
		path: "workflows/a_long_path/workflow.py",
		displayName: "Workflow",
		entityType: "workflow",
		localContent: null,
		remoteContent: "remote",
		isConflict: true,
		conflictType: "deleted_by_us",
		onResolve,
	};
	const { rerender } = render(
		<>
			<SyncDiffHeader preview={preview} onClose={onClose} />
			<SyncDiffResolution preview={preview} />
		</>,
	);
	await user.click(
		screen.getByRole("button", { name: "Keep local deletion" }),
	);
	expect(onResolve).toHaveBeenCalledWith("ours");
	rerender(
		<>
			<SyncDiffHeader preview={preview} onClose={onClose} />
			<SyncDiffResolution preview={{ ...preview, resolution: "ours" }} />
		</>,
	);
	expect(
		screen.getByRole("button", { name: "Keep local deletion" }),
	).toHaveAttribute("aria-pressed", "true");
	expect(screen.getByRole("button", { name: "Keep remote" })).toHaveAttribute(
		"aria-pressed",
		"false",
	);
	await user.click(screen.getByRole("button", { name: "Close diff view" }));
	expect(onClose).toHaveBeenCalledTimes(1);
});
