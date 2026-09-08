import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SourceOperationDialog } from "./SourceOperationDialog";

it("keeps a failed operation available for retry with readable fallback feedback", async () => {
	const user = userEvent.setup();
	const onConfirm = vi
		.fn()
		.mockRejectedValueOnce("unstructured failure")
		.mockResolvedValue(undefined);
	const onClose = vi.fn();
	render(
		<SourceOperationDialog
			title="Abort merge?"
			description="Return to the state before the pull."
			confirmLabel="Abort merge"
			pendingLabel="Aborting merge…"
			cancelLabel="Keep reviewing"
			onConfirm={onConfirm}
			onClose={onClose}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Abort merge" }));
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Couldn’t complete this operation. Try again.",
	);
	expect(onClose).not.toHaveBeenCalled();
	await user.click(screen.getByRole("button", { name: "Abort merge" }));
	expect(onConfirm).toHaveBeenCalledTimes(2);
	expect(onClose).toHaveBeenCalledTimes(1);
});

it("blocks a confirmation when freshness is lost but allows cancellation", async () => {
 const user = userEvent.setup(); const onConfirm = vi.fn(); const onClose = vi.fn();
 const props = {title:"Discard changes?",description:"Review the files.",confirmLabel:"Discard changes",pendingLabel:"Discarding…",cancelLabel:"Keep changes",onConfirm,onClose};
 const {rerender} = render(<SourceOperationDialog {...props} />);
 expect(screen.getByRole("button",{name:"Discard changes"})).toBeEnabled();
 rerender(<SourceOperationDialog {...props} unavailableReason="Refresh working changes first." />);
 expect(screen.getByRole("alert")).toHaveTextContent("Refresh working changes first.");
 await user.click(screen.getByRole("button",{name:"Discard changes"}));
 expect(onConfirm).not.toHaveBeenCalled();
 await user.click(screen.getByRole("button",{name:"Keep changes"}));
 expect(onClose).toHaveBeenCalledTimes(1);
});
