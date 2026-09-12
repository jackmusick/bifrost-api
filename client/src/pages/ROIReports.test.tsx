import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, within } from "@/test-utils";
import { ROIReports } from "./ROIReports";

const mockUseAuth = vi.fn();
const mockUseMediaQuery = vi.fn();
const mockUseReducedMotion = vi.fn();
const mockUseOrganizations = vi.fn();
const mockUseROISummary = vi.fn();
const mockUseROIByWorkflow = vi.fn();
const mockUseROIByOrganization = vi.fn();
const mockUseROITrends = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/useMediaQuery", () => ({
	useMediaQuery: (...args: unknown[]) => mockUseMediaQuery(...args),
}));

vi.mock("framer-motion", () => ({
	useReducedMotion: () => mockUseReducedMotion(),
}));

vi.mock("@/hooks/useOrganizations", () => ({
	useOrganizations: (...args: unknown[]) => mockUseOrganizations(...args),
}));

vi.mock("@/services/reports", () => ({
	useROISummary: (...args: unknown[]) => mockUseROISummary(...args),
	useROIByWorkflow: (...args: unknown[]) => mockUseROIByWorkflow(...args),
	useROIByOrganization: (...args: unknown[]) =>
		mockUseROIByOrganization(...args),
	useROITrends: (...args: unknown[]) => mockUseROITrends(...args),
}));

vi.mock("@/components/layout/ListPageHeader", () => ({
	ListPageHeader: ({
		title,
		description,
		actions,
	}: {
		title: string;
		description?: string;
		actions?: ReactNode;
	}) => (
		<header>
			<h1>{title}</h1>
			{description && <p>{description}</p>}
			{actions}
		</header>
	),
}));

vi.mock("@/components/forms/OrganizationSelect", () => ({
	OrganizationSelect: () => <div data-testid="organization-select" />,
}));

vi.mock("@/components/ui/date-range-picker", () => ({
	DateRangePicker: () => <div data-testid="date-range-picker" />,
}));

vi.mock("@/components/reports/ReportRecordList", () => ({
	ReportRecordList: ({
		label,
		records,
	}: {
		label: string;
		records: Array<{
			id: string;
			title: ReactNode;
			metrics: Array<{ label: string; value: ReactNode }>;
		}>;
	}) => (
		<section aria-label={label}>
			{records.map((record) => (
				<article key={record.id}>
					<h3>{record.title}</h3>
					{record.metrics.map((metric) => (
						<p key={metric.label}>
							{metric.label}: {metric.value}
						</p>
					))}
				</article>
			))}
		</section>
	),
}));

function makeSummary() {
	return {
		start_date: "2026-08-09",
		end_date: "2026-09-08",
		total_executions: 12,
		successful_executions: 11,
		total_time_saved: 360,
		total_value: 4800,
		time_saved_unit: "minutes",
		value_unit: "USD",
	};
}

function makeWorkflow() {
	return {
		workflows: [
			{
				workflow_id: "wf-1",
				workflow_name: "Ticket Sync",
				execution_count: 7,
				success_count: 7,
				time_saved_per_execution: 30,
				value_per_execution: 125,
				total_time_saved: 210,
				total_value: 875,
			},
		],
		total_workflows: 1,
		time_saved_unit: "minutes",
		value_unit: "USD",
	};
}

function makeTrends() {
	return {
		entries: [],
		granularity: "day",
		time_saved_unit: "minutes",
		value_unit: "USD",
	};
}

function renderPage() {
	return renderWithProviders(<ROIReports />);
}

beforeEach(() => {
	mockUseAuth.mockReturnValue({ isPlatformAdmin: true });
	mockUseMediaQuery.mockReturnValue(false);
	mockUseReducedMotion.mockReturnValue(false);
	mockUseOrganizations.mockReturnValue({ data: [] });
	mockUseROISummary.mockReturnValue({
		data: makeSummary(),
		isLoading: false,
		error: null,
		isFetching: false,
		refetch: vi.fn(),
	});
	mockUseROIByWorkflow.mockReturnValue({
		data: undefined,
		isLoading: false,
		error: null,
		isFetching: false,
		refetch: vi.fn(),
	});
	mockUseROIByOrganization.mockReturnValue({
		data: undefined,
		isLoading: false,
		error: null,
		isFetching: false,
		refetch: vi.fn(),
	});
	mockUseROITrends.mockReturnValue({
		data: makeTrends(),
		isLoading: false,
		error: null,
		isFetching: false,
		refetch: vi.fn(),
	});
});

describe("ROIReports read recovery", () => {
	it("shows retry affordances instead of empty claims when section reads fail with no cache", async () => {
		const workflowRefetch = vi.fn();
		const orgRefetch = vi.fn();
		const trendRefetch = vi.fn();

		mockUseROIByWorkflow.mockReturnValue({
			data: undefined,
			isLoading: false,
			error: new Error("workflow read failed"),
			isFetching: false,
			refetch: workflowRefetch,
		});
		mockUseROIByOrganization.mockReturnValue({
			data: undefined,
			isLoading: false,
			error: new Error("organization read failed"),
			isFetching: false,
			refetch: orgRefetch,
		});
		mockUseROITrends.mockReturnValue({
			data: undefined,
			isLoading: false,
			error: new Error("trend read failed"),
			isFetching: false,
			refetch: trendRefetch,
		});

		await renderPage();

		expect(
			screen.getByText(
				/Could not update the workflow breakdown, organization breakdown, trend chart\./,
			),
		).toBeVisible();
		expect(screen.getByText("Couldn't load workflow ROI.")).toBeVisible();
		expect(
			screen.getByText("Couldn't load organization ROI."),
		).toBeVisible();
		expect(screen.getByText("Couldn't load ROI trend data.")).toBeVisible();
		expect(
			screen.queryByText("No workflow data available for this period"),
		).not.toBeInTheDocument();
		expect(
			screen.queryByText(
				"No organization data available for this period",
			),
		).not.toBeInTheDocument();
		expect(
			screen.queryByText("No trend data available for this period"),
		).not.toBeInTheDocument();

		const workflowAlert = screen
			.getByText("Couldn't load workflow ROI.")
			.closest<HTMLElement>('[role="alert"]');
		expect(workflowAlert).toBeTruthy();
		await within(workflowAlert!)
			.getByRole("button", {
				name: "Retry loading",
			})
			.click();
		expect(workflowRefetch).toHaveBeenCalledTimes(1);
	});

	it("retains cached workflow rows and exposes retry while the read is failing", async () => {
		const workflowRefetch = vi.fn();

		mockUseROIByWorkflow.mockReturnValue({
			data: makeWorkflow(),
			isLoading: false,
			error: new Error("workflow read failed"),
			isFetching: false,
			refetch: workflowRefetch,
		});

		await renderPage();

		expect(
			within(
				screen.getByRole("region", { name: "workflow ROI" }),
			).getByText("Ticket Sync"),
		).toBeVisible();
		expect(
			screen.getByText(/Previously loaded records are shown below\./),
		).toBeVisible();
		expect(
			screen.queryByText("No workflow data available for this period"),
		).not.toBeInTheDocument();
		const workflowAlert = screen
			.getByText(/Couldn't load workflow ROI\./)
			.closest<HTMLElement>('[role="alert"]');
		expect(workflowAlert).toBeTruthy();
		await within(workflowAlert!)
			.getByRole("button", {
				name: "Retry loading",
			})
			.click();
		expect(workflowRefetch).toHaveBeenCalledTimes(1);
	});
});
