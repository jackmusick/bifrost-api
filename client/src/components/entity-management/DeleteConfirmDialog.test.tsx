import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { DeleteConfirmDialog } from "./DeleteConfirmDialog";

it("lists the entities to delete and respects the blocking deleting state", async () => {
	const user = userEvent.setup();
	const onOpenChange = vi.fn();
	const onCancel = vi.fn();
	const onConfirm = vi.fn();

	const { rerender } = render(
		<DeleteConfirmDialog
			open
			onOpenChange={onOpenChange}
			entities={[
				{ id: "a", name: "Alpha Workflow", entityType: "workflow" },
				{ id: "b", name: "Beta App", entityType: "app", slug: "beta-app" },
			]}
			isDeleting={false}
			onConfirm={onConfirm}
			onCancel={onCancel}
		/>,
	);

	expect(screen.getByRole("dialog")).toBeInTheDocument();
	expect(screen.getByText("Alpha Workflow")).toBeInTheDocument();
	expect(screen.getByText("Beta App")).toBeInTheDocument();
	expect(screen.getByText("Apps will be permanently deleted.")).toBeInTheDocument();

	await user.click(screen.getByRole("button", { name: "Cancel" }));
	expect(onCancel).toHaveBeenCalledOnce();

	await user.click(screen.getByRole("button", { name: "Delete 2 entities" }));
	expect(onConfirm).toHaveBeenCalledOnce();

	rerender(
		<DeleteConfirmDialog
			open
			onOpenChange={onOpenChange}
			entities={[{ id: "a", name: "Alpha Workflow", entityType: "workflow" }]}
			isDeleting
			onConfirm={onConfirm}
			onCancel={onCancel}
		/>,
	);

	expect(screen.getByRole("button", { name: "Delete workflow" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	expect(screen.queryByRole("button", { name: /close/i })).not.toBeInTheDocument();
});
