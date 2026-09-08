import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes, useLocation } from "react-router-dom";

import { renderWithProviders, screen } from "@/test-utils";

const mockIsDesktop = vi.hoisted(() => vi.fn(() => true));
vi.mock("@/hooks/useMediaQuery", () => ({ useIsDesktop: () => mockIsDesktop() }));

const mockUseInfiniteAgentRuns = vi.hoisted(() => vi.fn());
const mockUseRerunAgentRun = vi.hoisted(() => vi.fn());

vi.mock("@/services/agentRuns", () => ({
	useInfiniteAgentRuns: (params: unknown) => mockUseInfiniteAgentRuns(params),
	useAgentRunListStream: () => undefined,
	useRerunAgentRun: () => mockUseRerunAgentRun(),
}));

import { AgentRunsPanel } from "./AgentRunsPanel";

function NavigationStateProbe() {
	const location = useLocation();
	return (
		<pre data-testid="navigation-state">
			{JSON.stringify(location.state)}
		</pre>
	);
}

const run = {
	id: "run-1",
	agent_id: "agent-1",
	agent_name: "Service Desk Triage",
	trigger_type: "manual",
	status: "completed",
	iterations_used: 2,
	tokens_used: 1200,
	asked: "Triage ticket 428950",
	did: "Triaged the ticket.",
	input: {},
	output: {},
	verdict: null,
	created_at: "2026-07-23T12:00:00Z",
	started_at: "2026-07-23T12:00:00Z",
};
const secondPageRun = {
	...run,
	id: "run-26",
	asked: "Triage ticket 428976",
};

beforeEach(() => {
	mockIsDesktop.mockReturnValue(true);
	mockUseInfiniteAgentRuns.mockReturnValue({
		data: { pages: [{ items: [run], total: 1 }] },
		isLoading: false,
		hasNextPage: false,
		isFetchingNextPage: false,
		fetchNextPage: vi.fn(),
	});
	mockUseRerunAgentRun.mockReturnValue({
		mutate: vi.fn(),
		isPending: false,
	});
});

describe("AgentRunsPanel", () => {
	it("uses the same 25-run Previous and Next pagination as workflows", async () => {
		mockUseInfiniteAgentRuns.mockReturnValue({
			data: {
				pages: [
					{ items: [run], total: 50 },
					{ items: [secondPageRun], total: 50 },
				],
			},
			isLoading: false,
			hasNextPage: false,
			isFetchingNextPage: false,
			fetchNextPage: vi.fn(),
		});

		const { user } = renderWithProviders(
			<Routes>
				<Route path="/history" element={<AgentRunsPanel />} />
			</Routes>,
			{ initialEntries: ["/history?type=agents"] },
		);

		expect(mockUseInfiniteAgentRuns).toHaveBeenCalledWith({ pageSize: 25 });
		expect(screen.getByRole("row", { name: /428950/ })).toBeInTheDocument();
		expect(screen.queryByRole("row", { name: /428976/ })).not.toBeInTheDocument();
		expect(screen.getByText("1")).toHaveAttribute("aria-current", "page");

		await user.click(screen.getByLabelText("Go to next page"));
		expect(screen.queryByRole("row", { name: /428950/ })).not.toBeInTheDocument();
		expect(screen.getByRole("row", { name: /428976/ })).toBeInTheDocument();
		expect(screen.getByText("2")).toHaveAttribute("aria-current", "page");

		await user.click(screen.getByLabelText("Go to previous page"));
		expect(screen.getByRole("row", { name: /428950/ })).toBeInTheDocument();
	});

	it("constrains the table and progressively collapses secondary columns", () => {
		renderWithProviders(
			<Routes>
				<Route path="/history" element={<AgentRunsPanel />} />
			</Routes>,
			{ initialEntries: ["/history?type=agents"] },
		);

		const table = screen.getByRole("table");
		expect(table.parentElement?.parentElement).toHaveClass(
			"min-h-0",
			"min-w-0",
		);
		expect(screen.getByRole("columnheader", { name: "Agent" })).toHaveClass(
			"w-full",
			"sm:w-40",
		);
		expect(screen.getByRole("columnheader", { name: "Asked" })).toHaveClass(
			"hidden",
			"sm:table-cell",
		);
		expect(screen.getByRole("columnheader", { name: "Duration" })).toHaveClass(
			"hidden",
			"lg:table-cell",
		);
		expect(screen.getByRole("columnheader", { name: "Verdict" })).toHaveClass(
			"hidden",
			"xl:table-cell",
		);
		expect(screen.getByRole("columnheader", { name: "Started" })).toHaveClass(
			"hidden",
			"xl:table-cell",
		);
	});

	it("keeps fleet run history as the origin when opening a run", async () => {
		const { user } = renderWithProviders(
			<Routes>
				<Route path="/history" element={<AgentRunsPanel />} />
				<Route
					path="/agents/:agentId/runs/:runId"
					element={<NavigationStateProbe />}
				/>
			</Routes>,
			{ initialEntries: ["/history?type=agents"] },
		);

		await user.click(
			screen.getByRole("row", { name: /Service Desk Triage.*Completed/i }),
		);
		expect(screen.getByTestId("navigation-state")).toHaveTextContent(
			JSON.stringify({
				agentRunOrigin: {
					href: "/history?type=agents",
					label: "Back to run history",
				},
			}),
		);
	});
});


it("shows mobile records and preserves the return destination for keyboard navigation", async () => {
	mockIsDesktop.mockReturnValue(false);
	const { user } = renderWithProviders(<Routes><Route path="/history" element={<AgentRunsPanel />} /><Route path="/agents/:agentId/runs/:runId" element={<NavigationStateProbe />} /></Routes>, {initialEntries: ["/history?type=agents"]});
	expect(screen.queryByRole("table")).not.toBeInTheDocument();
	expect(screen.getByText("Triage ticket 428950")).toBeInTheDocument();
	expect(screen.getByText("Not reviewed")).toBeInTheDocument();
	const link = screen.getByRole("link", {name: "Service Desk Triage"});
	link.focus();
	await user.keyboard("{Enter}");
	expect(screen.getByTestId("navigation-state")).toHaveTextContent('"href":"/history?type=agents"');
});

it("distinguishes initial lookup failure from no runs and offers retry", async () => {
	const refetch = vi.fn();
	mockUseInfiniteAgentRuns.mockReturnValue({data: undefined, isLoading: false, isError: true, isFetching: false, refetch});
	const {user} = renderWithProviders(<AgentRunsPanel />);
	expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load agent runs");
	expect(screen.queryByText("No agent runs yet.")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", {name:"Retry loading agent runs"}));
	expect(refetch).toHaveBeenCalledOnce();
});

it("retains cached runs when refresh fails and retries loading", async () => {
 const refetch = vi.fn();
 mockUseInfiniteAgentRuns.mockReturnValue({data: {pages: [{items: [run], total: 1}]}, isLoading: false, isError: true, isFetching: false, refetch});
 const {user} = renderWithProviders(<AgentRunsPanel />);
 expect(screen.getByRole("row", {name: /Service Desk Triage.*Completed/i})).toBeVisible();
 expect(screen.getByRole("alert")).toHaveTextContent("Previously loaded records");
 await user.click(screen.getByRole("button", {name: "Retry loading"}));
 expect(refetch).toHaveBeenCalledOnce();
});

it("retains a failed rerun with focused feedback and retries the same source", async () => {
 const mutate = vi.fn().mockImplementationOnce((_params, callbacks) => callbacks.onError()).mockImplementationOnce((_params, callbacks) => callbacks.onSuccess({run_id: "retried-run"}));
 mockUseRerunAgentRun.mockReturnValue({mutate, isPending: false});
 const {user} = renderWithProviders(<Routes><Route path="/history" element={<AgentRunsPanel />} /><Route path="/agents/:agentId/runs/:runId" element={<NavigationStateProbe />} /></Routes>, {initialEntries: ["/history?type=agents"]});
 await user.click(screen.getByTestId("rerun-run-1"));
 expect(screen.getByRole("alert")).toHaveFocus();
 expect(screen.getByRole("alert")).toHaveTextContent("Service Desk Triage");
 expect(screen.getByRole("row", {name: /Service Desk Triage.*Completed/i})).toBeVisible();
 await user.click(screen.getByRole("button", {name: "Retry rerun"}));
 expect(mutate).toHaveBeenNthCalledWith(2, {params: {path: {run_id: "run-1"}}}, expect.any(Object));
 expect(screen.getByTestId("navigation-state")).toHaveTextContent('"href":"/history?type=agents"');
});

it("retries a failed next-page request while retaining the current records", async () => {
 const fetchNextPage = vi.fn().mockResolvedValue({data: {pages: [{items:[run],total:26},{items:[secondPageRun],total:26}]}});
 mockUseInfiniteAgentRuns.mockReturnValue({data: {pages: [{items:[run],total:26}]},isLoading:false,isError:true,isFetchNextPageError:true,isFetchingNextPage:false,hasNextPage:true,fetchNextPage});
 const {user} = renderWithProviders(<AgentRunsPanel />);
 expect(screen.getByRole("alert")).toHaveTextContent("still on page 1");
 expect(screen.getByRole("row", {name: /428950/})).toBeVisible();
 expect(screen.queryByRole("button", {name: "Retry loading"})).not.toBeInTheDocument();
 await user.click(screen.getByRole("button", {name: "Retry next page"}));
 expect(fetchNextPage).toHaveBeenCalledOnce();
});
