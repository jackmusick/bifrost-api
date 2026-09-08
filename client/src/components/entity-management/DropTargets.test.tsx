import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
const { register } = vi.hoisted(() => ({ register: vi.fn(() => vi.fn()) }));
vi.mock("@atlaskit/pragmatic-drag-and-drop/element/adapter", () => ({ dropTargetForElements: register }));
import { OrgDropTarget } from "./DropTargets";

it("routes button and drag selections to review and blocks both while busy", async () => {
	const user = userEvent.setup();
	const onDrop = vi.fn();
	const { rerender } = render(<OrgDropTarget organization={null} selectedIds={["selected"]} onDrop={onDrop} />);
	await user.click(screen.getByRole("button", { name: /Apply Global/ }));
	expect(onDrop).toHaveBeenCalledWith(["selected"], null);
	type Registration = { canDrop: (args: unknown) => boolean; onDrop: (args: unknown) => void };
	const latest = () => (register.mock.calls.at(-1) as unknown as [Registration])[0];
	const source = { source: { data: { type: "entity", entityIds: ["dragged"], entityCount: 1 } } };
	expect(latest().canDrop(source)).toBe(true);
	latest().onDrop(source);
	expect(onDrop).toHaveBeenLastCalledWith(["dragged"], null);
	rerender(<OrgDropTarget organization={null} selectedIds={["selected"]} onDrop={onDrop} disabled />);
	expect(screen.getByRole("button", { name: /Apply Global/ })).toBeDisabled();
	expect(latest().canDrop(source)).toBe(false);
	latest().onDrop(source);
	expect(onDrop).toHaveBeenCalledTimes(2);
});
