/**
 * LogsView Component
 *
 * Displays logs table with the execution drawer.
 * All filters are managed by the parent ExecutionHistory component.
 */

import { useState, useMemo, useCallback } from "react";
import type { DateRange } from "react-day-picker";

import { useLogs, type LogFilters, type LogListEntry } from "@/hooks/useLogs";
import { Button } from "@/components/ui/button";
import { LogsTable } from "./LogsTable";
import { ExecutionDrawer } from "./ExecutionDrawer";

interface LogsViewProps {
	workflowId?: string;
	/** Organization ID filter from parent */
	filterOrgId?: string | null;
	/** Date range filter from parent */
	dateRange?: DateRange;
	/** Search term from parent (searches workflow name and message) */
	searchTerm?: string;
	/** Selected log level from parent */
	logLevel?: string;
}

/**
 * Internal component that handles the actual logs fetching and display.
 * This is wrapped by LogsView which provides a key to reset state when filters change.
 */
function LogsViewInner({
	filterOrgId,
	workflowId,
	dateRange,
	searchTerm,
	logLevel,
}: LogsViewProps) {
	// Pagination state - resets when parent remounts us via key change
	const [currentToken, setCurrentToken] = useState<string | undefined>();
	const [pageStack, setPageStack] = useState<string[]>([]);

	// Drawer state
	const [selectedExecutionId, setSelectedExecutionId] = useState<
		string | null
	>(null);
	const [drawerOpen, setDrawerOpen] = useState(false);

	// Build filters object from props
	const filters: LogFilters = useMemo(() => {
		const result: LogFilters = {};
		if (workflowId) result.workflow_id = workflowId;
		if (filterOrgId === null) result.global_only = true;

		if (filterOrgId !== undefined && filterOrgId !== null) {
			result.organization_id = filterOrgId;
		}

		if (searchTerm?.trim()) {
			result.message_search = searchTerm.trim();
		}

		if (dateRange?.from) {
			const startDate = new Date(dateRange.from);
			startDate.setHours(0, 0, 0, 0);
			result.start_date = startDate.toISOString();

			const endDate = new Date(dateRange.to || dateRange.from);
			endDate.setHours(23, 59, 59, 999);
			result.end_date = endDate.toISOString();
		}

		if (logLevel && logLevel !== "all") {
			result.levels = logLevel;
		}

		return result;
	}, [filterOrgId, workflowId, searchTerm, dateRange, logLevel]);

	// Fetch logs
	const { data, isLoading, isFetching, isError, refetch } = useLogs(
		filters,
		currentToken,
		true,
		{ preservePageData: true },
	);

	const logs = data?.logs ?? [];
	const continuationToken = data?.continuation_token;

	// Pagination handlers
	const handleNextPage = useCallback(() => {
		if (continuationToken) {
			setPageStack((prev) => [...prev, currentToken || ""]);
			setCurrentToken(continuationToken);
		}
	}, [continuationToken, currentToken]);

	const handlePrevPage = useCallback(() => {
		if (pageStack.length > 0) {
			const newStack = [...pageStack];
			const previousToken = newStack.pop();
			setPageStack(newStack);
			setCurrentToken(previousToken || undefined);
		}
	}, [pageStack]);

	// Log click handler
	const handleLogClick = useCallback((log: LogListEntry) => {
		setSelectedExecutionId(log.execution_id);
		setDrawerOpen(true);
	}, []);

	return (
		<>
			{/* Table */}
			<div className="mt-4 flex min-h-0 min-w-0 flex-1 flex-col gap-4">
				{isError && (
					<div
						role="alert"
						className="space-y-3 rounded-[var(--bf-radius-surface)] border border-border bg-card p-4"
					>
						<p>
							Couldn't load logs.
							{data
								? " Previously loaded logs are shown below."
								: ""}
						</p>
						<Button
							variant="outline"
							className="min-h-11"
							disabled={isFetching}
							onClick={() => void refetch()}
						>
							{isFetching ? "Retrying…" : "Retry loading logs"}
						</Button>
						{pageStack.length > 0 && !data && (
							<Button
								variant="outline"
								className="min-h-11"
								disabled={isFetching}
								onClick={handlePrevPage}
							>
								Back to previous page
							</Button>
						)}
					</div>
				)}
				{(!isError || data) && (
					<LogsTable
						logs={logs}
						isLoading={isLoading}
						isFetching={isFetching}
						continuationToken={continuationToken}
						onNextPage={handleNextPage}
						onPrevPage={handlePrevPage}
						canGoBack={pageStack.length > 0}
						currentPage={pageStack.length + 1}
						onLogClick={handleLogClick}
					/>
				)}
			</div>

			{/* Execution Drawer */}
			<ExecutionDrawer
				executionId={selectedExecutionId}
				open={drawerOpen}
				onOpenChange={setDrawerOpen}
			/>
		</>
	);
}

/**
 * LogsView wrapper that uses a key to reset pagination state when filters change.
 * This is the React-idiomatic pattern for resetting child state on prop changes.
 */
export function LogsView(props: LogsViewProps) {
	const { filterOrgId, workflowId, dateRange, searchTerm, logLevel } = props;

	// Generate a key from filter values - when this changes, the inner component remounts
	// and all its internal state (pagination) resets to initial values
	const filterKey = `${workflowId ?? "all"}-${filterOrgId === null ? "global" : (filterOrgId ?? "all")}-${searchTerm ?? ""}-${dateRange?.from?.toISOString() ?? "none"}-${dateRange?.to?.toISOString() ?? "none"}-${logLevel ?? "all"}`;

	return <LogsViewInner key={filterKey} {...props} />;
}
