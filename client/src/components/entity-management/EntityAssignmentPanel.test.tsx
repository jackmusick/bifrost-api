import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { EntityAssignmentPanel } from "./EntityAssignmentPanel";
import type { EntityWithScope } from "./types";

it("reviews a selection snapshot, blocks duplicate submission, and retains failures for retry", async () => {
	const user = userEvent.setup();
	const entities = [{ id: "a", name: "Alpha", entityType: "workflow" }, { id: "b", name: "Beta", entityType: "form" }] as EntityWithScope[];
	let reject!: (cause: Error) => void;
	const onOrganization = vi.fn().mockImplementationOnce(() => new Promise<void>((_, fail) => { reject = fail; })).mockResolvedValue(undefined);
	const props = { entities, organizations: [], roles: [], disabled: false, onOrganization, onAccess: vi.fn().mockResolvedValue(undefined), selectedIds: new Set(["a"]) };
	const { rerender } = render(<EntityAssignmentPanel {...props} />);
	const apply = screen.getByRole("button", { name: "Apply Global to 1 selected entities" });
	await user.click(apply);
	expect(screen.getByRole("list", { name: "Entities to update" })).toHaveTextContent("Alpha");
	rerender(<EntityAssignmentPanel {...props} selectedIds={new Set(["b"])} />);
	await user.click(screen.getByRole("button", { name: "Apply changes" }));
	expect(onOrganization).toHaveBeenCalledWith(["a"], null);
	expect(screen.getByRole("button", { name: "Applying…" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(screen.getByRole("dialog")).toBeInTheDocument();
	reject(new Error("Alpha could not be updated"));
	await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Alpha could not be updated"));
	await user.click(screen.getByRole("button", { name: "Retry changes" }));
	await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
	expect(onOrganization).toHaveBeenCalledTimes(2);
	expect(onOrganization).toHaveBeenLastCalledWith(["a"], null);
});

it("requires a selection and routes keyboard access assignment through review", async () => {
	const user = userEvent.setup();
	const onAccess = vi.fn().mockResolvedValue(undefined);
	const props = { entities: [{ id: "a", name: "Alpha", entityType: "workflow" }] as EntityWithScope[], organizations: [], roles: [], disabled: false, onOrganization: vi.fn(), onAccess };
	const { rerender } = render(<EntityAssignmentPanel {...props} selectedIds={new Set()} />);
	expect(screen.getByRole("button", { name: "Apply Clear roles to 0 selected entities" })).toBeDisabled();
	rerender(<EntityAssignmentPanel {...props} selectedIds={new Set(["a"])} />);
	screen.getByRole("button", { name: "Apply Clear roles to 1 selected entities" }).focus();
	await user.keyboard("{Enter}");
	expect(screen.getByText("This removes all role assignments and sets access to role-based.")).toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Cancel" }));
	expect(onAccess).not.toHaveBeenCalled();
	screen.getByRole("button", { name: "Apply Everyone except external users to 1 selected entities" }).focus();
	await user.keyboard("{Enter}");
	await user.click(screen.getByRole("button", { name: "Apply changes" }));
	await waitFor(() => expect(onAccess).toHaveBeenCalledWith(["a"], "authenticated"));
});
