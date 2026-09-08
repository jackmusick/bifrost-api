import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { ExecutionCancelAction } from "./ExecutionHistory/components/ExecutionCancelAction";
import { ExecutionCleanupDialog } from "./ExecutionHistory/components/ExecutionCleanupDialog";
import { useState, useMemo, Fragment } from "react";
import { useSearchParams } from "react-router-dom";
import {
	RefreshCw,
	History as HistoryIcon,
	Globe,
	AlertCircle,
	SearchX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
	DataTableFooter,
} from "@/components/ui/data-table";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { LogsView } from "./ExecutionHistory/components/LogsView";
import { ExecutionRecord } from "./ExecutionHistory/components/ExecutionRecord";
import { ExecutionDrawer } from "./ExecutionHistory/components/ExecutionDrawer";
import { RunStatusBadge } from "@/components/execution";
import {
	formatRunDuration,
	formatRunTime,
	groupExecutionsByDay,
	runAnchorDate,
	summarizeRuns,
} from "./ExecutionHistory/components/historyView";
import { FAILURE_STATUSES } from "@/lib/execution-buckets";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AgentRunsPanel } from "@/components/agents/AgentRunsPanel";
import { Bot as BotIcon, Workflow as WorkflowIcon } from "lucide-react";
import { useExecutions } from "@/hooks/useExecutions";
import { useExecutionHistory } from "@/hooks/useExecutionStream";
import { WorkflowSelector } from "@/components/forms/WorkflowSelector";
import { useScopeStore } from "@/stores/scopeStore";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import { useAuth } from "@/contexts/AuthContext";
import { useOrganizations } from "@/hooks/useOrganizations";
import { formatDate } from "@/lib/utils";
import { SearchBox } from "@/components/search/SearchBox";
import { useSearch } from "@/hooks/useSearch";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import type { ExecutionFilters } from "@/lib/client-types";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { ListToolbar } from "@/components/layout/ListToolbar";
import {
	Pagination,
	PaginationContent,
	PaginationItem,
	PaginationLink,
	PaginationNext,
	PaginationPrevious,
} from "@/components/ui/pagination";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import type { DateRange } from "react-day-picker";
import type { components } from "@/lib/v1";

type Organization = components["schemas"]["OrganizationPublic"];
type ExecutionStatus =
	| components["schemas"]["ExecutionStatus"]
	| "Cancelling"
	| "Cancelled";

/** Statuses with a tab on this page — accepted via the `?status=` param. */
const STATUS_TABS: ExecutionStatus[] = [
	"Success",
	"Running",
	"Failed",
	"Pending",
	"Scheduled",
];

export function ExecutionHistory() {
	const isDesktop = useIsDesktop();
 const queryClient = useQueryClient();
 const agentRunsFetching = useIsFetching({queryKey: ["agent-runs-infinite"]});
 const logsFetching = useIsFetching({queryKey: ["get", "/api/executions/logs"]});
	const [filtersOpen, setFiltersOpen] = useState(false);
	const [searchParams, setSearchParams] = useSearchParams();
	const { isPlatformAdmin, user } = useAuth();
	const [filterOrgId, setFilterOrgId] = useState<string | null | undefined>(
		undefined,
	);
	const workflowIdFilter = searchParams.get("workflow") || "";
	// `?status=` is the single source of truth for the status tab — derived
	// from the URL and written back through setSearchParams (same pattern as
	// `historyType` below), so tab changes survive refresh/back and Clear
	// filters can't leave a stale param behind.
	const statusParam = searchParams.get("status")?.toLowerCase();
	const statusFilter: ExecutionStatus | "all" =
		STATUS_TABS.find((s) => s.toLowerCase() === statusParam) ?? "all";
	const setStatusFilter = (value: ExecutionStatus | "all") => {
		setSearchParams(
			(prev) => {
				const next = new URLSearchParams(prev);
				if (value === "all") {
					next.delete("status");
				} else {
					next.set("status", value);
				}
				return next;
			},
			{ replace: true },
		);
	};
	const [searchTerm, setSearchTerm] = useState("");
	const [dateRange, setDateRange] = useState<DateRange | undefined>();
	const [showLocal, setShowLocal] = useState(false);
	const [viewMode, setViewMode] = useState<"executions" | "logs">("executions");
	const historyType = (searchParams.get("type") === "agents"
		? "agents"
		: "workflows") as "workflows" | "agents";
	const [logLevelFilter, setLogLevelFilter] = useState<string>("all");
	const [drawerExecutionId, setDrawerExecutionId] = useState<string | null>(null);
	const [drawerOpen, setDrawerOpen] = useState(false);
	// IDs that were optimistically flipped to Cancelled after a successful 200.
	const [optimisticCancelledIds, setOptimisticCancelledIds] = useState<
		Set<string>
	>(new Set());
	const isGlobalScope = useScopeStore((state) => state.isGlobalScope);
	const orgId = useScopeStore((state) => state.scope.orgId);

	// Enable real-time updates for history page
	// Platform admins subscribe to GLOBAL channel, regular users to their own channel
	const scope = isGlobalScope ? "GLOBAL" : orgId || "GLOBAL";
	useExecutionHistory({
		scope,
		enabled: true,
		isPlatformAdmin,
		userId: user?.id,
	});
	// Pagination state - stack of continuation tokens for "back" navigation
	const [pageStack, setPageStack] = useState<(string | null)[]>([]);
	const [currentToken, setCurrentToken] = useState<string | undefined>(
		undefined,
	);

	// Fetch organizations for the org name lookup (platform admins only)
	const { data: organizations } = useOrganizations({
		enabled: isPlatformAdmin,
	});

	// Helper to get organization name from ID
	const getOrgName = (orgId: string | null | undefined): string => {
		if (!orgId) return "Global";
		const org = organizations?.find((o: Organization) => o.id === orgId);
		return org?.name || orgId;
	};

	// Build filters including date range and local executions toggle.
	// The Failed tab means the whole failure group (Failed, Timeout, Stuck,
	// CompletedWithErrors) — the same set the dashboard's "N failed" link
	// counts — so it sends the comma-separated group to the server's
	// match-any status filter instead of a single exact status.
	const filters = useMemo(() => {
		const baseFilters: Record<string, string | boolean> = {};
		if (statusFilter === "Failed") {
			baseFilters.status = Array.from(FAILURE_STATUSES).join(",");
		} else if (statusFilter !== "all") {
			baseFilters.status = statusFilter;
		}

		// Add excludeLocal filter (inverse of showLocal)
		baseFilters.excludeLocal = !showLocal;

		// Workflow IDs are implementation details; only admins get this filter.
		if (isPlatformAdmin && workflowIdFilter) {
			baseFilters.workflow_id = workflowIdFilter;
		}

		if (dateRange?.from) {
			// Set start to beginning of day (00:00:00)
			const startDate = new Date(dateRange.from);
			startDate.setHours(0, 0, 0, 0);

			// Set end to end of day (23:59:59.999)
			// If no end date selected, use the same day as start
			const endDate = new Date(dateRange.to || dateRange.from);
			endDate.setHours(23, 59, 59, 999);

			return {
				...baseFilters,
				start_date: startDate.toISOString(),
				end_date: endDate.toISOString(),
			};
		}

		return baseFilters;
	}, [statusFilter, dateRange, showLocal, isPlatformAdmin, workflowIdFilter]);

	// Pass filterOrgId to backend for filtering (undefined = all, null = global only)
	// For platform admins, undefined means show all. For non-admins, backend handles filtering.
	const {
		data: response,
		isFetching,
		isError,
		refetch,
	} = useExecutions(
		isPlatformAdmin ? filterOrgId : undefined,
		filters as ExecutionFilters,
		currentToken,
	);

	// Memoize executions to prevent dependency issues
	const executions = useMemo(
		() => response?.executions || [],
		[response?.executions],
	);
	const nextToken = response?.continuation_token || null;
 const historyRefreshing = historyType === "agents" ? agentRunsFetching > 0 : viewMode === "logs" ? logsFetching > 0 : isFetching;
	const hasMore = nextToken !== null;

	const handleViewDetails = (execution_id: string) => {
		setDrawerExecutionId(execution_id);
		setDrawerOpen(true);
	};

	const handleCancelled = (id: string, scheduled: boolean) => {
        if (scheduled) setOptimisticCancelledIds(previous => new Set([...previous, id]));
        void refetch();
    };

	// Apply search filter
	const filteredExecutions = useSearch(executions, searchTerm, [
		"workflow_name",
		"executed_by_name",
		"execution_id",
		(exec) => exec.status,
	]);

	// Pagination handlers
	const handleNextPage = () => {
		if (nextToken) {
			// Push current state to stack for "back" navigation
			setPageStack([...pageStack, currentToken || null]);
			setCurrentToken(nextToken);
		}
	};

	const handlePreviousPage = () => {
		if (pageStack.length > 0) {
			// Pop from stack to go back
			const newStack = [...pageStack];
			const previousToken = newStack.pop();
			setPageStack(newStack);
			setCurrentToken(previousToken || undefined);
		}
	};

	// Reset pagination when filters change. Adjust during render with a
	// previous-key sentinel rather than via setState-in-effect.
	const filtersKey = `${statusFilter}|${dateRange?.from?.toISOString() ?? ""}|${dateRange?.to?.toISOString() ?? ""}|${showLocal}|${filterOrgId ?? ""}|${workflowIdFilter ?? ""}`;
	const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey);
	if (prevFiltersKey !== filtersKey) {
		setPrevFiltersKey(filtersKey);
		setPageStack([]);
		setCurrentToken(undefined);
	}

	// Drop optimistic-cancel entries once the server echoes the row as
	// Cancelled (or it drops off the current page). Keeps the set from
	// growing forever. Adjust during render with a previous-executions-ref
	// sentinel rather than via setState-in-effect.
	const [prevExecutionsRef, setPrevExecutionsRef] = useState(executions);
	if (prevExecutionsRef !== executions) {
		setPrevExecutionsRef(executions);
		if (optimisticCancelledIds.size > 0) {
			const visibleIds = new Set(executions.map((e) => e.execution_id));
			const next = new Set<string>();
			for (const id of optimisticCancelledIds) {
				const row = executions.find((e) => e.execution_id === id);
				if (!row) continue; // dropped off page → forget
				if (row.status === "Cancelled") continue; // server caught up
				if (visibleIds.has(id)) next.add(id);
			}
			if (next.size !== optimisticCancelledIds.size) {
				setOptimisticCancelledIds(next);
			}
		}
	}

	// Whether any narrowing filter is active — drives which empty state shows.
	const hasActiveFilters =
		searchTerm !== "" ||
		statusFilter !== "all" ||
		dateRange !== undefined ||
		(isPlatformAdmin && (workflowIdFilter !== "" || filterOrgId !== undefined));

	const handleClearFilters = () => {
		setSearchTerm("");
		setDateRange(undefined);
		setFilterOrgId(undefined);
		setSearchParams(
			(prev) => {
				const next = new URLSearchParams(prev);
				next.delete("workflow");
				next.delete("status");
				return next;
			},
			{ replace: true },
		);
	};

	// Header rollup: page-level run counts. Honest about scope — these are
	// the runs currently loaded, with "more available" when paginated.
	const rollup = useMemo(() => summarizeRuns(executions), [executions]);

	// Day groups preserve server (newest-first) order.
	const dayGroups = useMemo(
		() => groupExecutionsByDay(filteredExecutions),
		[filteredExecutions],
	);

	// One source of truth for the column count (admins get the Org column).
	const columnCount = isPlatformAdmin ? 7 : 6;

	const showPaginationFooter = hasMore || pageStack.length > 0;

	return (
		<section
			aria-labelledby="history-heading"
			className="mx-auto flex min-h-full lg:h-full lg:min-h-0 w-full max-w-7xl min-w-0 flex-col gap-4 pb-1 sm:gap-6"
		>
			<ListPageHeader
				className="shrink-0 flex-row flex-nowrap items-start gap-4"
				title={<span id="history-heading">History</span>}
				description={
					<span data-testid="history-summary">
						{historyType === "agents" ? (
							"View agent run history across the fleet"
						) : viewMode === "logs" ? "Search execution logs across workflows" : rollup.total > 0 ? (
							<>
								{rollup.total} run{rollup.total !== 1 ? "s" : ""}
								{rollup.succeeded > 0 && (
									<> · {rollup.succeeded} succeeded</>
								)}
								{rollup.failed > 0 && (
									<>
										{" · "}
										<span className="font-medium text-destructive">
											{rollup.failed} failed
										</span>
									</>
								)}
								{rollup.running > 0 && (
									<> · {rollup.running} in progress</>
								)}
								{rollup.scheduled > 0 && (
									<> · {rollup.scheduled} scheduled</>
								)}
								{hasMore && <> · more available</>}
							</>
						) : (
							"Every workflow run — manual, scheduled, or form-triggered"
						)}
					</span>
				}
				actions={
					<>
						{isPlatformAdmin && <ExecutionCleanupDialog onCleaned={() => void refetch()} />}

						<Button
							variant="outline"
							size="icon-lg"
							onClick={() => historyType === "agents" ? void queryClient.invalidateQueries({queryKey: ["agent-runs-infinite"]}) : viewMode === "logs" ? void queryClient.invalidateQueries({queryKey: ["get", "/api/executions/logs"]}) : void refetch()}
							disabled={historyRefreshing}
							aria-label="Refresh execution history"
						>
							<RefreshCw
								className={`h-4 w-4 motion-reduce:animate-none ${historyRefreshing ? "animate-spin" : ""}`}
							/>
						</Button>
					</>
				}
				actionsClassName="shrink-0 self-start"
			/>
			{isPlatformAdmin ? (
				<ToggleGroup
					type="single"
					value={historyType}
					onValueChange={(value: string) => {
						if (!value) return;
						setSearchParams(
							(prev) => {
								const next = new URLSearchParams(prev);
								if (value === "workflows") {
									next.delete("type");
								} else {
									next.set("type", value);
								}
								return next;
							},
							{ replace: true },
						);
					}}
					aria-label="Execution history type"
					size="lg"
					className="mt-1 grid w-full grid-cols-2 justify-start sm:flex sm:w-auto"
					data-testid="history-type-toggle"
				>
					<ToggleGroupItem
						value="workflows"
						aria-label="Workflows"
						className="gap-1.5"
					>
						<WorkflowIcon className="h-3.5 w-3.5" />
						Workflows
					</ToggleGroupItem>
					<ToggleGroupItem
						value="agents"
						aria-label="Agents"
						className="gap-1.5"
					>
						<BotIcon className="h-3.5 w-3.5" />
						Agents
					</ToggleGroupItem>
				</ToggleGroup>
			) : null}

			{historyType === "agents" ? <AgentRunsPanel /> : null}

			{historyType === "workflows" ? (
			<>
			<ListToolbar className="items-stretch">
				<div className="flex min-w-0 flex-col gap-3">
					<div className="flex min-w-0 items-start gap-2">
					<SearchBox
						value={searchTerm}
						onChange={setSearchTerm}
						placeholder={viewMode === "logs"
							? (isDesktop ? "Search log messages..." : "Search logs…")
							: (isDesktop ? "Search by workflow name, user, or execution ID..." : "Search runs…")}
						aria-label={viewMode === "logs" ? "Search log messages..." : "Search by workflow name, user, or execution ID..."}
						className="min-w-0 flex-1 lg:min-w-[240px]"
					/>
						{!isDesktop && (
							<Button
								variant="outline"
								className="min-h-11 shrink-0 gap-2 px-3"
								aria-label={filtersOpen ? "Hide filters" : "Show filters"}
								aria-expanded={filtersOpen}
								aria-controls="history-filters"
								onClick={() => setFiltersOpen((open) => !open)}
							>
								Filters
								{(workflowIdFilter ||
									filterOrgId !== undefined ||
									dateRange?.from) && (
									<span className="text-xs text-muted-foreground">
										Active
									</span>
								)}
							</Button>
						)}
					</div>

					<div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center">

						<div
							id="history-filters"
							data-testid="history-filters"
							hidden={!isDesktop && !filtersOpen}
							className={
								isDesktop
									? "flex min-w-0 flex-wrap items-center gap-3"
									: filtersOpen
										? "flex flex-col gap-3 rounded-[var(--bf-radius-surface)] border border-border bg-card p-3"
										: "hidden"
							}
						>
							{isPlatformAdmin && (
								<WorkflowSelector
									value={workflowIdFilter || undefined}
									onChange={(value) => {
										const newFilter = value ?? "";
										setSearchParams(
											(prev) => {
												const next = new URLSearchParams(prev);
												if (newFilter) {
													next.set("workflow", newFilter);
												} else {
													next.delete("workflow");
												}
												return next;
											},
											{ replace: true },
										);
									}}
									variant="combobox"
									allowClear={true}
									placeholder="All workflows"
									className="w-full min-w-0 lg:w-48"
								/>
							)}
							{isPlatformAdmin && (
								<div className="w-full min-w-0 lg:w-56">
									<OrganizationSelect
										value={filterOrgId}
										onChange={setFilterOrgId}
										showAll={true}
										showGlobal={true}
										placeholder="All organizations"
									/>
								</div>
							)}
							<DateRangePicker
								dateRange={dateRange}
								onDateRangeChange={setDateRange}
								className="w-full min-w-0 sm:w-auto"
							/>
						</div>
						<div
							data-testid="history-controls"
							className="flex flex-wrap items-center gap-3 lg:ml-auto"
						>
							{/* Show Local Executions - only for executions view */}
							{viewMode === "executions" && (
								<div className="flex items-center gap-2">
									<Checkbox
										id="show-local"
										checked={showLocal}
										onCheckedChange={(checked) =>
											setShowLocal(checked === true)
										}
									/>
									<Label
										htmlFor="show-local"
										className="flex min-h-11 cursor-pointer items-center whitespace-nowrap text-sm font-normal text-muted-foreground"
									>
										Show local
									</Label>
								</div>
							)}
							{isPlatformAdmin && (
								<>
									<Separator
										orientation="vertical"
										className="h-5"
									/>
									<div className="flex items-center gap-2">
										<Switch
											id="view-mode"
											checked={viewMode === "logs"}
											onCheckedChange={(checked) =>
												setViewMode(
													checked ? "logs" : "executions",
												)
											}
										/>
										<Label
											htmlFor="view-mode"
											className="flex min-h-11 cursor-pointer items-center whitespace-nowrap text-sm font-normal text-muted-foreground"
										>
											Logs view
										</Label>
									</div>
								</>
							)}
						</div>
					</div>
				</div>
			</ListToolbar>

			{/* Status/Level Tabs and Content */}
			{viewMode === "logs" ? (
				<Tabs
					value={logLevelFilter}
					onValueChange={setLogLevelFilter}
					className="flex flex-col flex-1 min-h-0"
				>
					{/* Log Level Tabs */}
					{!isDesktop ? <Select value={logLevelFilter} onValueChange={setLogLevelFilter}>
                        <SelectTrigger aria-label="Log level" className="w-full min-h-11"><SelectValue /></SelectTrigger>
                        <SelectContent position="popper"><SelectItem value="all" className="min-h-11">All levels</SelectItem><SelectItem value="DEBUG" className="min-h-11">Debug</SelectItem><SelectItem value="INFO" className="min-h-11">Info</SelectItem><SelectItem value="WARNING" className="min-h-11">Warning</SelectItem><SelectItem value="ERROR" className="min-h-11">Error</SelectItem><SelectItem value="CRITICAL" className="min-h-11">Critical</SelectItem></SelectContent>
                    </Select> : (<div className="no-scrollbar w-fit max-w-full overflow-x-auto sm:overflow-visible">
						<TabsList className="w-max justify-start">
							<TabsTrigger value="all">All</TabsTrigger>
							<TabsTrigger value="DEBUG">Debug</TabsTrigger>
							<TabsTrigger value="INFO">Info</TabsTrigger>
							<TabsTrigger value="WARNING">Warning</TabsTrigger>
							<TabsTrigger value="ERROR">Error</TabsTrigger>
							<TabsTrigger value="CRITICAL">Critical</TabsTrigger>
						</TabsList>
					</div>)}

					{/* Logs View */}
					<LogsView
                        workflowId={workflowIdFilter || undefined}
						filterOrgId={filterOrgId}
						dateRange={dateRange}
						searchTerm={searchTerm}
						logLevel={logLevelFilter}
					/>
				</Tabs>
			) : (
				<Tabs
					value={statusFilter}
					onValueChange={(v) =>
						setStatusFilter(v as ExecutionStatus | "all")
					}
					className="flex min-h-0 min-w-0 flex-1 flex-col"
				>
				{!isDesktop ? <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as ExecutionStatus | "all")}>
                        <SelectTrigger aria-label="Run status" className="w-full min-h-11"><SelectValue /></SelectTrigger>
                        <SelectContent position="popper"><SelectItem value="all" className="min-h-11">All statuses</SelectItem><SelectItem value="Success" className="min-h-11">Completed</SelectItem><SelectItem value="Running" className="min-h-11">Running</SelectItem><SelectItem value="Failed" className="min-h-11">Failed</SelectItem><SelectItem value="Pending" className="min-h-11">Pending</SelectItem><SelectItem value="Scheduled" className="min-h-11">Scheduled</SelectItem></SelectContent>
                    </Select> : (<div className="no-scrollbar w-fit max-w-full overflow-x-auto sm:overflow-visible">
					<TabsList className="w-max justify-start">
						<TabsTrigger value="all">All</TabsTrigger>
						<TabsTrigger value="Success">Completed</TabsTrigger>
						<TabsTrigger value="Running">Running</TabsTrigger>
						<TabsTrigger value="Failed">Failed</TabsTrigger>
						<TabsTrigger value="Pending">Pending</TabsTrigger>
						<TabsTrigger value="Scheduled">Scheduled</TabsTrigger>
					</TabsList>
				</div>)}

				<TabsContent
					value={statusFilter}
					aria-label={!isDesktop ? "Execution results" : undefined}
					className="mt-4 flex-1 min-h-0"
				>
					{isError ? (
						<div
							className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
							data-testid="history-error"
						>
							<AlertCircle className="h-10 w-10 text-destructive" />
							<h3 className="mt-4 text-lg font-semibold">
								Couldn't load execution history
							</h3>
							<p className="mt-2 text-sm text-muted-foreground">
								Something went wrong fetching runs. Your data
								is safe — try again.
							</p>
							<Button
								variant="outline"
								className="mt-4 min-h-11"
								onClick={() => refetch()}
							>
								<RefreshCw className="mr-2 h-4 w-4" />
								Try again
							</Button>
						</div>
					) : isFetching && !executions.length ? (
						<div
							className="overflow-hidden rounded-2xl bg-card shadow-sm ring-1 ring-foreground/5 dark:ring-foreground/10"
							data-testid="history-loading"
						>
							<div className="border-b px-4 py-3">
								<Skeleton className="h-4 w-44" />
							</div>
							{Array.from({ length: 8 }).map((_, i) => (
								<div
									key={i}
									className="flex items-center gap-6 border-b px-4 py-4 last:border-0"
								>
									<Skeleton className="h-4 w-48" />
									<Skeleton className="h-5 w-24 rounded-full" />
									<Skeleton className="h-4 w-28" />
									<Skeleton className="ml-auto h-4 w-20" />
									<Skeleton className="h-4 w-12" />
								</div>
							))}
						</div>
					) : filteredExecutions.length > 0 ? (
						!isDesktop ? (
							<div className="space-y-6" aria-label="Execution records">
								{dayGroups.map((group) => (
									<section key={group.key} className="space-y-2" aria-label={group.label}>
										<h2 className="text-xs font-semibold text-muted-foreground">{group.label}</h2>
										<ul className="divide-y divide-border rounded-[var(--bf-radius-surface)] border border-border bg-card">
											{group.executions.map((execution) => (
                                            <ExecutionRecord
                                                key={execution.execution_id}
                                                execution={execution}
                                                status={optimisticCancelledIds.has(execution.execution_id) ? "Cancelled" : execution.status}
                                                organizationName={isPlatformAdmin ? (execution.org_id ? getOrgName(execution.org_id) : "Global") : undefined}
                                                onOpen={() => handleViewDetails(execution.execution_id)}
                                                actions={<ExecutionCancelAction executionId={execution.execution_id} workflowName={execution.workflow_name} status={optimisticCancelledIds.has(execution.execution_id) ? "Cancelled" : execution.status} scheduledAt={execution.scheduled_at} onCancelled={scheduled => handleCancelled(execution.execution_id, scheduled)} onRefresh={() => void refetch()} />}
                                            />
                                        ))}
										</ul>
									</section>
								))}
								{showPaginationFooter && <nav aria-label="Execution pages" className="flex flex-wrap items-center justify-between gap-2">
									<Button variant="outline" className="min-h-11" disabled={pageStack.length === 0 || isFetching} onClick={handlePreviousPage}>Previous</Button>
									<span className="text-sm text-muted-foreground" aria-current="page">Page {pageStack.length + 1}</span>
									<Button variant="outline" className="min-h-11" disabled={!hasMore || isFetching} onClick={handleNextPage}>Next</Button>
								</nav>}
							</div>
						) : (
						<DataTable className="min-w-0">
							<DataTableHeader>
								<DataTableRow>
									{isPlatformAdmin && (
										<DataTableHead className="hidden w-px xl:table-cell">
											Organization
										</DataTableHead>
									)}
									<DataTableHead className="w-full">Workflow</DataTableHead>
									<DataTableHead className="w-px">Status</DataTableHead>
									<DataTableHead className="hidden w-px xl:table-cell">Run by</DataTableHead>
									<DataTableHead className="hidden w-px lg:table-cell">Started</DataTableHead>
									<DataTableHead className="hidden w-px text-right xl:table-cell">
										Duration
									</DataTableHead>
									<DataTableHead className="w-px text-right"></DataTableHead>
								</DataTableRow>
							</DataTableHeader>
							<DataTableBody>
								{dayGroups.map((group) => (
									<Fragment key={group.key}>
										<DataTableRow
											className="border-b hover:bg-transparent"
											data-testid="history-day-row"
										>
											<DataTableCell
												colSpan={columnCount}
												className="bg-muted/40 dark:bg-background/50 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
											>
												{group.label}
											</DataTableCell>
										</DataTableRow>
										{group.executions.map((execution) => {
											// Apply optimistic flip: if the user just
											// confirmed cancel on this row, render it
											// as Cancelled until refetch converges.
											const displayStatus =
												optimisticCancelledIds.has(
													execution.execution_id,
												)
													? "Cancelled"
													: execution.status;

											const isGlobalExecution =
												!execution.org_id;
											const anchor = runAnchorDate(execution);
											const anchorIso =
												execution.started_at ??
												execution.scheduled_at ??
												execution.completed_at;
											const duration = formatRunDuration(
												execution.started_at,
												execution.completed_at,
											);
											const hasErrorDetail =
												!!execution.error_message &&
												(displayStatus === "Failed" ||
													displayStatus === "Timeout" ||
													displayStatus ===
														"CompletedWithErrors");

											return (
												<DataTableRow
													key={execution.execution_id}
													data-testid="execution-row"
													data-execution-id={
														execution.execution_id
													}
													clickable
													href={`/history/${execution.execution_id}`}
													onClick={(e) => {
														if (e.metaKey || e.ctrlKey || e.button === 1) return;
														handleViewDetails(
															execution.execution_id,
														);
													}}
												>
													{isPlatformAdmin && (
														<DataTableCell className="hidden w-px whitespace-nowrap text-sm text-muted-foreground xl:table-cell">
															{isGlobalExecution ? (
																<span className="inline-flex items-center gap-1.5">
																	<Globe className="h-3.5 w-3.5" />
																	Global
																</span>
															) : (
																getOrgName(
																	execution.org_id,
																)
															)}
														</DataTableCell>
													)}
													<DataTableCell
														className="w-full max-w-0"
														data-testid="execution-workflow-cell"
													>
														<div className="truncate font-mono text-sm font-medium">
															{execution.workflow_name}
														</div>
														{hasErrorDetail && (
															<div
																className="mt-0.5 truncate text-xs text-destructive/90"
																title={
																	execution.error_message ??
																	undefined
																}
															>
																{
																	execution.error_message
																}
															</div>
														)}
														<div
															className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground xl:hidden"
														>
															{isPlatformAdmin && (
																<span>
																	{isGlobalExecution
																		? "Global"
																		: getOrgName(execution.org_id)}
																</span>
															)}
															<span className="xl:hidden">
																by {execution.executed_by_name}
															</span>
															<span className="lg:hidden">
																{anchorIso
																	? formatRunTime(anchorIso)
																	: "Not started"}
															</span>
															<span className="xl:hidden">
																{duration ?? "No duration"}
															</span>
														</div>
													</DataTableCell>
													<DataTableCell className="w-px whitespace-nowrap">
														<RunStatusBadge
															status={displayStatus}
															scheduledAt={
																execution.scheduled_at
															}
														/>
													</DataTableCell>
													<DataTableCell className="hidden w-px whitespace-nowrap text-sm text-muted-foreground xl:table-cell">
														{execution.executed_by_name}
													</DataTableCell>
													<DataTableCell
														className="hidden w-px whitespace-nowrap text-sm text-muted-foreground lg:table-cell"
														title={
															anchor
																? formatDate(anchor)
																: undefined
														}
													>
														{anchorIso
															? formatRunTime(
																	anchorIso,
																)
															: "—"}
													</DataTableCell>
													<DataTableCell className="hidden w-px whitespace-nowrap text-right text-sm tabular-nums text-muted-foreground xl:table-cell">
														{duration ?? "—"}
													</DataTableCell>
													<DataTableCell className="w-px text-right">
														<div className="flex items-center justify-end gap-1">
															<ExecutionCancelAction compact executionId={execution.execution_id} workflowName={execution.workflow_name} status={optimisticCancelledIds.has(execution.execution_id) ? "Cancelled" : execution.status} scheduledAt={execution.scheduled_at} onCancelled={scheduled => handleCancelled(execution.execution_id, scheduled)} onRefresh={() => void refetch()} />
														</div>
													</DataTableCell>
												</DataTableRow>
											);
										})}
									</Fragment>
								))}
							</DataTableBody>
							{showPaginationFooter && (
								<DataTableFooter>
									<DataTableRow>
										<DataTableCell
											colSpan={columnCount}
											className="p-0"
										>
											<div className="px-6 py-3 flex items-center justify-center">
												<Pagination>
													<PaginationContent>
														<PaginationItem>
															<PaginationPrevious
																onClick={(e) => {
																	e.preventDefault();
																	handlePreviousPage();
																}}
																className={
																	pageStack.length ===
																		0 ||
																	isFetching
																		? "pointer-events-none opacity-50"
																		: "cursor-pointer"
																}
																aria-disabled={
																	pageStack.length ===
																		0 ||
																	isFetching
																}
															/>
														</PaginationItem>
														<PaginationItem>
															<PaginationLink
																isActive
															>
																{pageStack.length +
																	1}
															</PaginationLink>
														</PaginationItem>
														<PaginationItem>
															<PaginationNext
																onClick={(e) => {
																	e.preventDefault();
																	handleNextPage();
																}}
																className={
																	!hasMore ||
																	isFetching
																		? "pointer-events-none opacity-50"
																		: "cursor-pointer"
																}
																aria-disabled={
																	!hasMore ||
																	isFetching
																}
															/>
														</PaginationItem>
													</PaginationContent>
												</Pagination>
											</div>
										</DataTableCell>
									</DataTableRow>
								</DataTableFooter>
							)}
						</DataTable>
						)
					) : hasActiveFilters ? (
						<div
							className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
							data-testid="history-empty-filtered"
						>
							<SearchX className="h-10 w-10 text-muted-foreground" />
							<h3 className="mt-4 text-lg font-semibold">
								No runs match your filters
							</h3>
							<p className="mt-2 text-sm text-muted-foreground">
								Try widening the date range or clearing the
								search and status filters.
							</p>
							<Button
								variant="outline"
								className="mt-4"
								onClick={handleClearFilters}
							>
								Clear filters
							</Button>
						</div>
					) : (
						<div
							className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
							data-testid="history-empty"
						>
							<HistoryIcon className="h-10 w-10 text-muted-foreground" />
							<h3 className="mt-4 text-lg font-semibold">
								No runs yet
							</h3>
							<p className="mt-2 max-w-sm text-sm text-muted-foreground">
								When a workflow runs — manually, on a
								schedule, or from a form — it shows up here
								with its status and timing.
							</p>
						</div>
					)}
				</TabsContent>
				</Tabs>
			)}
			</>
			) : null}

			<ExecutionDrawer
				executionId={drawerExecutionId}
				open={drawerOpen}
				onOpenChange={setDrawerOpen}
				onExecutionChange={setDrawerExecutionId}
			/>
		</section>
	);
}
