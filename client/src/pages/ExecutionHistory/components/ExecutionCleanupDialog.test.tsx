import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ExecutionCleanupDialog } from "./ExecutionCleanupDialog";
const api = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn() }));
vi.mock("@/lib/api-client", () => ({ apiClient: api }));
const records = {
	executions: [
		{
			execution_id: "one",
			workflow_name: "review_run",
			executed_by_name: "Operator",
			status: "Running",
			started_at: null,
		},
	],
};
beforeEach(() => vi.resetAllMocks());
it("distinguishes HTTP read failure from empty and retries", async () => {
	const user = userEvent.setup();
	api.GET.mockResolvedValueOnce({
		error: { detail: "failed" },
	}).mockResolvedValueOnce({ data: records });
	render(<ExecutionCleanupDialog onCleaned={vi.fn()} />);
	await user.click(
		screen.getByRole("button", { name: "Cleanup stuck executions" }),
	);
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"Could not load",
	);
	expect(screen.queryByText("No stuck executions")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Retry loading" }));
	expect(await screen.findByText("review_run")).toBeVisible();
});
it("retains records on HTTP cleanup failure and locks dismissal while retrying", async () => {
	const user = userEvent.setup();
	const onCleaned = vi.fn();
	api.GET.mockResolvedValue({ data: records });
	let release!: (value: unknown) => void;
	api.POST.mockResolvedValueOnce({
		error: { detail: "failed" },
	}).mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				release = resolve;
			}),
	);
	render(<ExecutionCleanupDialog onCleaned={onCleaned} />);
	await user.click(
		screen.getByRole("button", { name: "Cleanup stuck executions" }),
	);
	await screen.findByText("review_run");
	await user.click(
		screen.getByRole("button", { name: "Cleanup 1 execution" }),
	);
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"Could not clean up",
	);
	expect(screen.getByText("review_run")).toBeVisible();
	await user.click(screen.getByRole("button", { name: "Retry cleanup" }));
	expect(
		screen.getByRole("button", { name: "Cancel" }),
	).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(screen.getByRole("dialog")).toBeVisible();
	expect(api.POST).toHaveBeenCalledTimes(2);
	await act(async () => release({ data: { cleaned: 1 } }));
	expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	expect(onCleaned).toHaveBeenCalledOnce();
});
