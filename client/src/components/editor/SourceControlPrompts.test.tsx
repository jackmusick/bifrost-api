import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SourceDeletionPrompt } from "./SourceControlPrompts";
const entities = Array.from({ length: 8 }, (_, i) => ({
	action: "removed" as const,
	entity_type: "workflow",
	name: `Full entity name ${i}`,
	path: `workflows/long_path_${i}.py`,
}));
it("allows review of every pending deletion and separates dismissal from confirmation", async () => {
	const user = userEvent.setup(),
		onConfirm = vi.fn(),
		onDismiss = vi.fn();
	const { rerender } = render(
		<SourceDeletionPrompt
			entities={entities}
			disabled={false}
			isPending={false}
			onConfirm={onConfirm}
			onDismiss={onDismiss}
		/>,
	);
	expect(screen.getAllByRole("listitem")).toHaveLength(8);
	expect(screen.getByText(entities[7].path)).toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Dismiss" }));
	expect(onDismiss).toHaveBeenCalledTimes(1);
	expect(onConfirm).not.toHaveBeenCalled();
	await user.click(screen.getByRole("button", { name: "Delete and sync" }));
	expect(onConfirm).toHaveBeenCalledTimes(1);
	rerender(
		<SourceDeletionPrompt
			entities={entities}
			disabled={false}
			isPending
			onConfirm={onConfirm}
			onDismiss={onDismiss}
		/>,
	);
	expect(
		screen.getByRole("button", { name: "Deleting and syncing…" }),
	).toBeDisabled();
	expect(screen.getByRole("button", { name: "Dismiss" })).toBeDisabled();
});
