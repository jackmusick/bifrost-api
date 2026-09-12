import { beforeEach, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { LogsView } from "./LogsView";

const mockLogs = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/useLogs", () => ({
	useLogs: (...args: unknown[]) => mockLogs(...args),
}));
vi.mock("@/hooks/useMediaQuery", () => ({ useIsDesktop: () => false }));
vi.mock("./ExecutionDrawer", () => ({
	ExecutionDrawer: ({
		open,
		executionId,
	}: {
		open: boolean;
		executionId: string;
	}) => (open ? <div role="dialog">{executionId}</div> : null),
}));
const log = {
	id: 1,
	execution_id: "run-one",
	organization_name: "Customer operations",
	workflow_name: "reconcile_agreements",
	level: "WARNING",
	message: "Agreement renewal requires review.\nApproval remains pending.",
	timestamp: "2026-09-06T12:00:00Z",
};
beforeEach(() => {
	vi.clearAllMocks();
	mockLogs.mockReturnValue({
		data: { logs: [log], continuation_token: "next" },
		isLoading: false,
		isFetching: false,
		isError: false,
	});
});

it("opens the execution drawer from a keyboard-accessible mobile log record", async () => {
	const { user } = renderWithProviders(<LogsView />);
	expect(screen.queryByRole("table")).not.toBeInTheDocument();
	expect(screen.getByTestId("log-record")).toHaveTextContent(
		"Approval remains pending.",
	);
	screen.getByRole("link", { name: log.workflow_name }).focus();
	await user.keyboard("{Enter}");
	expect(screen.getByRole("dialog")).toHaveTextContent("run-one");
});

it("resets the cursor when only the date-range end changes", async () => {
	const from = new Date("2026-09-01T00:00:00Z");
	const { user, rerender } = renderWithProviders(
		<LogsView dateRange={{ from, to: new Date("2026-09-02T00:00:00Z") }} />,
	);
	await user.click(screen.getByRole("button", { name: "Next" }));
	expect(mockLogs).toHaveBeenLastCalledWith(
		expect.any(Object),
		"next",
		true,
		{ preservePageData: true },
	);
	rerender(
		<LogsView dateRange={{ from, to: new Date("2026-09-03T00:00:00Z") }} />,
	);
	expect(mockLogs).toHaveBeenLastCalledWith(
		expect.any(Object),
		undefined,
		true,
		{ preservePageData: true },
	);
	expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
});

it("shows a retryable failure instead of an empty result", async () => {
	const refetch = vi.fn();
	mockLogs.mockReturnValue({
		data: undefined,
		isError: true,
		isFetching: false,
		refetch,
	});
	const { user } = renderWithProviders(<LogsView />);
	expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load logs.");
	expect(
		screen.queryByText("No logs found matching your filters."),
	).not.toBeInTheDocument();
	await user.click(
		screen.getByRole("button", { name: "Retry loading logs" }),
	);
	expect(refetch).toHaveBeenCalledOnce();
});

it("keeps cached logs visible while a refresh fails", () => {
	mockLogs.mockReturnValue({
		data: { logs: [log], continuation_token: "next" },
		isError: true,
		isFetching: true,
	});
	renderWithProviders(<LogsView />);
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Previously loaded logs are shown below.",
	);
	expect(screen.getByTestId("log-record")).toBeInTheDocument();
	expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});

it("returns to the previous log page after a failed next-page request", async () => {
	mockLogs.mockImplementation((_filters, token) =>
		token
			? {
					data: undefined,
					isError: true,
					isFetching: false,
					refetch: vi.fn(),
				}
			: {
					data: { logs: [log], continuation_token: "next" },
					isError: false,
					isLoading: false,
					isFetching: false,
				},
	);
	const { user } = renderWithProviders(<LogsView />);
	await user.click(screen.getByRole("button", { name: "Next" }));
	expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load logs");
	await user.click(
		screen.getByRole("button", { name: "Back to previous page" }),
	);
	expect(screen.getByTestId("log-record")).toHaveTextContent(
		log.workflow_name,
	);
	expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
});

it("passes the selected workflow ID and resets pagination when it changes", async () => {
	const { user, rerender } = renderWithProviders(
		<LogsView workflowId="workflow-one" />,
	);
	expect(mockLogs).toHaveBeenLastCalledWith(
		expect.objectContaining({ workflow_id: "workflow-one" }),
		undefined,
		true,
		{ preservePageData: true },
	);
	await user.click(screen.getByRole("button", { name: "Next" }));
	rerender(<LogsView workflowId="workflow-two" />);
	expect(mockLogs).toHaveBeenLastCalledWith(
		expect.objectContaining({ workflow_id: "workflow-two" }),
		undefined,
		true,
		{ preservePageData: true },
	);
	expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
});

it("distinguishes global logs from all organizations and resets its cursor", async () => {
	const { user, rerender } = renderWithProviders(<LogsView />);
	await user.click(screen.getByRole("button", { name: "Next" }));
	rerender(<LogsView filterOrgId={null} />);
	expect(mockLogs).toHaveBeenLastCalledWith(
		expect.objectContaining({ global_only: true }),
		undefined,
		true,
		{ preservePageData: true },
	);
});
