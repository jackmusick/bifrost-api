import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, renderWithProviders, screen, waitFor } from "@/test-utils";
import { OrphanedWorkflowDialog } from "./OrphanedWorkflowDialog";
import type { components } from "@/lib/v1";

type Workflow = components["schemas"]["WorkflowMetadata"];

const mocks = vi.hoisted(() => ({
	authFetch: vi.fn(),
	toast: {
		success: vi.fn(),
		warning: vi.fn(),
		error: vi.fn(),
	},
}));

vi.mock("sonner", () => ({
	toast: mocks.toast,
}));

vi.mock("@/lib/api-client", () => ({
	authFetch: (...args: unknown[]) => mocks.authFetch(...args),
}));

function makeResponse(ok: boolean, data: unknown) {
	return {
		ok,
		json: async () => data,
	} as const;
}

function makeWorkflow(overrides: Partial<Workflow> = {}): Workflow {
	return {
		id: "wf-orphaned",
		name: "orphaned_workflow",
		function_name: "orphaned_workflow",
		type: "workflow",
		organization_id: null,
		source_file_path: "workflows/orphaned.py",
		relative_file_path: "workflows/orphaned.py",
		created_at: "2026-09-07T00:00:00Z",
		...overrides,
	} as Workflow;
}

beforeEach(() => {
	mocks.authFetch.mockReset();
	mocks.toast.success.mockReset();
	mocks.toast.warning.mockReset();
	mocks.toast.error.mockReset();
});

describe("OrphanedWorkflowDialog", () => {
	it("shows a retryable load error and preserves the recovery actions", async () => {
		mocks.authFetch
			.mockResolvedValueOnce(makeResponse(false, { detail: "nope" }))
			.mockResolvedValueOnce(makeResponse(true, { references: [] }))
			.mockResolvedValueOnce(
				makeResponse(true, {
					replacements: [
						{
							path: "workflows/replacement.py",
							function_name: "replacement_workflow",
							signature: "replacement_workflow()",
							compatibility: "exact",
						},
					],
				}),
			)
			.mockResolvedValueOnce(makeResponse(true, { references: [] }));

		renderWithProviders(
			<OrphanedWorkflowDialog
				open={true}
				onClose={vi.fn()}
				workflow={makeWorkflow()}
			/>,
		);

		expect(
			await screen.findByText("Failed to load compatible replacements"),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Retry" })).toHaveClass(
			"min-h-11",
		);
		expect(
			screen.getByRole("button", { name: "Recreate File" }),
		).toHaveClass("min-h-11");

		fireEvent.click(screen.getByRole("button", { name: "Retry" }));

		await waitFor(() =>
			expect(
				screen.queryByText("Failed to load compatible replacements"),
			).not.toBeInTheDocument(),
		);
		expect(mocks.authFetch).toHaveBeenCalledTimes(4);
	});
});

it("keeps a pending recovery open and retries the failed action", async () => {
	let fail!: (value: unknown) => void;
	let attempts = 0;
	mocks.authFetch.mockImplementation((url: string) => {
		if (url.endsWith("/recreate")) {
			attempts++;
			return attempts === 1
				? new Promise((resolve) => {
						fail = resolve;
					})
				: Promise.resolve(makeResponse(true, {}));
		}
		return Promise.resolve(
			makeResponse(
				true,
				url.endsWith("/references")
					? { references: [] }
					: { replacements: [] },
			),
		);
	});
	const onClose = vi.fn();
	const { user } = renderWithProviders(
		<OrphanedWorkflowDialog
			open
			onClose={onClose}
			workflow={makeWorkflow()}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "Recreate File" }));
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
	expect(
		screen.getByRole("button", { name: "Recreate File" }),
	).toBeDisabled();
	fail(makeResponse(false, { detail: "Recovery temporarily unavailable" }));
	const error = await screen.findByRole("alert");
	expect(error).toHaveTextContent("Recovery temporarily unavailable");
	await waitFor(() => expect(error).toHaveFocus());
	await user.click(screen.getByRole("button", { name: "Retry" }));
	await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
	expect(attempts).toBe(2);
});

it("surfaces a failed dependency lookup and recovers its references", async () => {
	let failed = true;
	mocks.authFetch.mockImplementation((url: string) =>
		Promise.resolve(
			url.endsWith("/references")
				? makeResponse(
						!failed,
						failed
							? {}
							: {
									references: [
										{
											type: "form",
											id: "f1",
											name: "Service intake",
										},
									],
								},
					)
				: makeResponse(true, { replacements: [] }),
		),
	);
	const { user } = renderWithProviders(
		<OrphanedWorkflowDialog
			open
			onClose={vi.fn()}
			workflow={makeWorkflow()}
		/>,
	);
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"This workflow may still be in use.",
	);
	failed = false;
	await user.click(
		screen.getByRole("button", { name: "Retry dependencies" }),
	);
	expect(await screen.findByText("Service intake")).toBeVisible();
	expect(
		screen.queryByRole("button", { name: "Retry dependencies" }),
	).not.toBeInTheDocument();
});
