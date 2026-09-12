import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ExecutionCancelAction } from "./ExecutionCancelAction";
const mocks = vi.hoisted(() => ({ POST: vi.fn(), cancelExecution: vi.fn() }));
vi.mock("@/lib/api-client", () => ({ apiClient: { POST: mocks.POST } }));
vi.mock("@/hooks/useExecutions", () => ({
	cancelExecution: mocks.cancelExecution,
}));
beforeEach(() => vi.resetAllMocks());
it("retains scheduled confirmation after HTTP failure and locks pending retry", async () => {
	const user = userEvent.setup(),
		onCancelled = vi.fn();
	let release!: (value: unknown) => void;
	mocks.POST.mockResolvedValueOnce({
		error: { detail: "failed" },
	}).mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				release = resolve;
			}),
	);
	render(
		<ExecutionCancelAction
			executionId="one"
			workflowName="Review"
			status="Scheduled"
			onCancelled={onCancelled}
			onRefresh={vi.fn()}
		/>,
	);
	await user.click(
		screen.getByRole("button", { name: "Cancel scheduled execution" }),
	);
	await user.click(screen.getByRole("button", { name: "Confirm cancel" }));
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"Could not cancel",
	);
	await user.click(
		screen.getByRole("button", { name: "Retry cancellation" }),
	);
	expect(
		screen.getByRole("button", { name: "Keep scheduled" }),
	).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(screen.getByRole("alertdialog")).toBeVisible();
	await act(async () => release({ data: { status: "Cancelled" } }));
	expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
	expect(onCancelled).toHaveBeenCalledWith(true);
	expect(mocks.POST).toHaveBeenCalledTimes(2);
});
it("offers running cancellation retry and prevents duplicate pending requests", async () => {
	const user = userEvent.setup(),
		onCancelled = vi.fn();
	let release!: () => void;
	mocks.cancelExecution
		.mockRejectedValueOnce(new Error("failed"))
		.mockImplementationOnce(
			() =>
				new Promise<void>((resolve) => {
					release = resolve;
				}),
		);
	render(
		<ExecutionCancelAction
			executionId="one"
			workflowName="Review"
			status="Running"
			onCancelled={onCancelled}
			onRefresh={vi.fn()}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Cancel execution" }));
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"Could not cancel",
	);
	await user.click(
		screen.getByRole("button", { name: "Retry cancellation" }),
	);
	const pending = screen.getByRole("button", {
		name: "Cancelling execution",
	});
	expect(pending).toBeDisabled();
	await user.click(pending);
	expect(mocks.cancelExecution).toHaveBeenCalledTimes(2);
	await act(async () => release());
	expect(onCancelled).toHaveBeenCalledWith(false);
});
