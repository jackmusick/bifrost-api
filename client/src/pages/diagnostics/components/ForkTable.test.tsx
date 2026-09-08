import { act, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProcessInfo } from "@/services/workers";

const mocks = vi.hoisted(() => ({
	recycleAll: vi.fn(),
	toastSuccess: vi.fn(),
	toastError: vi.fn(),
}));

vi.mock("@/services/workers", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/services/workers")>();
	return {
		...actual,
		useRecycleAllProcesses: () => ({
			mutate: mocks.recycleAll,
		}),
	};
});

vi.mock("sonner", () => ({
	toast: {
		success: mocks.toastSuccess,
		error: mocks.toastError,
	},
}));

import { ForkTable } from "./ForkTable";

const processes: ProcessInfo[] = [
	{
		process_id: "proc-1",
		pid: 4120,
		state: "idle",
		current_execution_id: null,
		executions_completed: 12,
		started_at: null,
		uptime_seconds: 91,
		memory_mb: 128,
		is_alive: true,
	},
	{
		process_id: "proc-2",
		pid: 4121,
		state: "busy",
		current_execution_id: "exec-2",
		executions_completed: 8,
		started_at: null,
		uptime_seconds: 3723,
		memory_mb: 256,
		is_alive: true,
	},
];

const executions = new Map([
	[
		"proc-2",
		{
			execution_id: "exec-2",
			workflow_name: "Deploy nightly workspace sync",
			status: "RUNNING" as const,
			elapsed_seconds: 185,
		},
	],
]);

describe("ForkTable", () => {
	beforeEach(() => {
		mocks.recycleAll.mockReset();
		mocks.toastSuccess.mockReset();
		mocks.toastError.mockReset();
	});

	it("renders readable process records and keeps recycle retries tied to the same worker", async () => {
		const user = userEvent.setup();

		render(
			<ForkTable
				workerId="worker-1"
				processes={processes}
				executions={executions}
				containerMemoryMax={512 * 1024 * 1024}
			/>,
		);

		expect(
			screen.getByRole("list", { name: "Worker processes" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("columnheader", { name: "PID" }),
		).toBeInTheDocument();

		const records = screen.getAllByRole("listitem");
		expect(within(records[0]).getByText("PID")).toBeInTheDocument();
		expect(within(records[0]).getByText("Jobs")).toBeInTheDocument();
		expect(
			within(records[1]).getByText("Deploy nightly workspace sync"),
		).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Recycle All" }));

		const dialog = screen.getByRole("alertdialog");
		expect(dialog).toHaveTextContent(
			"This will gracefully restart all 2 fork(s) in worker-1.",
		);

		await user.click(
			within(dialog).getByRole("button", { name: "Recycle All" }),
		);

		expect(mocks.recycleAll).toHaveBeenCalledWith(
			{ workerId: "worker-1", reason: "manual_recycle" },
			expect.any(Object),
		);
		expect(
			within(dialog).getByRole("button", { name: "Recycling..." }),
		).toBeDisabled();

		await user.keyboard("{Escape}");
		expect(dialog).toBeVisible();
		act(() =>
			mocks.recycleAll.mock.calls[0][1].onError(
				new Error("worker unavailable"),
			),
		);
		await waitFor(() =>
			expect(within(dialog).getByRole("alert")).toHaveTextContent(
				"worker unavailable",
			),
		);
		expect(
			within(dialog).getByRole("button", { name: "Retry recycle" }),
		).toBeInTheDocument();
		expect(mocks.toastError).toHaveBeenCalledWith(
			"Recycle failed: worker unavailable",
		);
		expect(mocks.toastSuccess).not.toHaveBeenCalled();
		await user.click(
			within(dialog).getByRole("button", { name: "Retry recycle" }),
		);
		expect(mocks.recycleAll.mock.calls[0][0]).toEqual(
			mocks.recycleAll.mock.calls[1][0],
		);
		act(() => mocks.recycleAll.mock.calls[1][1].onSuccess());
		expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
	});
});
