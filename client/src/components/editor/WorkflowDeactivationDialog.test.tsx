import { act, renderWithProviders, screen, waitFor } from "@/test-utils";
import { expect, it, vi } from "vitest";
import { WorkflowDeactivationDialog } from "./WorkflowDeactivationDialog";
it("keeps choices through pending failure and retries them; reopening starts fresh", async () => {
	let reject: (reason: Error) => void = () => {};
	const resolve = vi
		.fn()
		.mockImplementationOnce(
			() =>
				new Promise<void>((_, fail) => {
					reject = fail;
				}),
		)
		.mockResolvedValue(undefined);
	const props = {
		open: true,
		pendingDeactivations: [
			{
				id: "a",
				name: "Alpha",
				function_name: "alpha",
				path: "alpha.py",
				decorator_type: "workflow" as const,
				has_executions: false,
				endpoint_enabled: false,
			},
		],
		availableReplacements: [],
		onResolve: resolve,
		onCancel: vi.fn(),
	};
	const { user, rerender } = renderWithProviders(
		<WorkflowDeactivationDialog {...props} />,
	);
	await user.click(screen.getByRole("combobox"));
	await user.click(screen.getByRole("option", { name: /Deactivate/ }));
	await user.click(screen.getByRole("button", { name: /Apply/ }));
	expect(screen.getByRole("combobox")).toBeDisabled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(props.onCancel).not.toHaveBeenCalled();
	await act(async () => reject(new Error("Synthetic failure")));
	await waitFor(() => expect(screen.getByRole("alert")).toHaveFocus());
	await user.click(screen.getByRole("button", { name: /Retry/ }));
	expect(resolve).toHaveBeenCalledTimes(2);
	expect(resolve.mock.calls[1]).toEqual([{}, ["a"]]);
	rerender(<WorkflowDeactivationDialog {...props} open={false} />);
	rerender(<WorkflowDeactivationDialog {...props} />);
	expect(screen.getByRole("button", { name: /Apply/ })).toBeDisabled();
});
