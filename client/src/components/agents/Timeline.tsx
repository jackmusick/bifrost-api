import { MarkdownContent } from "@/components/common/MarkdownContent";
import {
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useExecution } from "@/hooks/useExecutions";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
/**
 * Timeline has two deliberately different projections of a run:
 *
 * - Timeline: a user-facing activity story. It groups the executor's
 *   decision/call/result records into one operation and nests child runs.
 * - AdvancedTimeline: the exact step sequence with raw payload disclosure.
 */

import {
	useEffect,
	useId,
	useMemo,
	useRef,
	useState,
	type ReactNode,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
	AlertCircle,
	ArrowUpRight,
	Bot,
	Check,
	ChevronRight,
	CircleDot,
	Cpu,
	GitBranch,
	Loader2,
	MessageSquare,
	MessageSquareText,
	Wrench,
	Workflow,
	X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { formatCost, formatDuration, formatNumber } from "@/lib/utils";
import type { components } from "@/lib/v1";
import {
	createAgentRunNavigationState,
	type AgentRunNavigationOrigin,
} from "@/lib/agent-run-navigation";
import { useAgentRun } from "@/services/agentRuns";
import { VariablesTreeView } from "@/components/ui/variables-tree-view";

import { DidNarrative } from "./DidNarrative";
import { isEmptyJson } from "./JsonTree";
import {
	activityDomId,
	buildActivityReferenceIndex,
	buildRunActivity,
	type RunActivityItem,
} from "./run-activity";

type AgentRunStepResponse = components["schemas"]["AgentRunStepResponse"];
type AgentRunDetailResponse = components["schemas"]["AgentRunDetailResponse"];
type AgentRunChildResponse = components["schemas"]["AgentRunChildResponse"];
type BulkExpansionRequest = { expanded: boolean; token: number } | null;

const ACTIVE_RUN_STATUSES = new Set(["queued", "running", "cancelling"]);
const EMPTY_CHILD_RUN_IDS: string[] = [];
const EMPTY_CHILD_RUNS: AgentRunChildResponse[] = [];

export interface TimelineProps {
	toolbarLeading?: ReactNode;
	toolbarActions?: ReactNode;
	inspector?: "sheet" | "inline";
	steps: AgentRunStepResponse[] | null | undefined;
	childRunIds?: string[] | null;
	childRuns?: AgentRunChildResponse[] | null;
	runStatus?: string | null;
	showTechnicalDetails?: boolean;
	highlightedActivityId?: string | null;
	expandedDelegationIds?: ReadonlySet<string>;
	onDelegationExpandedChange?: (
		activityId: string,
		expanded: boolean,
	) => void;
	restoreActivityId?: string | null;
	onInspectionChange?: (inspecting: boolean) => void;
	joinedRows?: boolean;
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
	/** Used only to keep pathological/cyclic history from nesting forever. */
	depth?: number;
}

export function Timeline({
	toolbarLeading,
	toolbarActions,
	inspector = "sheet",
	steps,
	childRunIds = EMPTY_CHILD_RUN_IDS,
	childRuns = EMPTY_CHILD_RUNS,
	runStatus,
	highlightedActivityId = null,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId = null,
	onInspectionChange,
	joinedRows = false,
	onOpenChildRun,
	childRunOrigin,
	depth = 0,
}: TimelineProps) {
	const activity = useMemo(
		() => buildRunActivity(steps, childRunIds, childRuns),
		[steps, childRunIds, childRuns],
	);
	const compactInspector = useMediaQuery("(max-width: 1023px)");
	const inlineInspector = inspector === "inline" && !compactInspector;
	const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
	const inspectionTrigger = useRef<HTMLElement | null>(null);
	// Navigation restoration is one-shot; bulk expansion remounts rows.
	const [restoredActivity, setRestoredActivity] = useState<string | null>(
		null,
	);
	const [selectedActivityId, setSelectedActivityId] = useState<string | null>(
		null,
	);
	const [selectedSnapshot, setSelectedSnapshot] = useState<{
		item: RunActivityItem;
		sourceRunId?: string;
	} | null>(null);
	const [bulkExpansionRequest, setBulkExpansionRequest] =
		useState<BulkExpansionRequest>(null);
	const { data: rawSelectedSource } = useAgentRun(
		selectedSnapshot?.sourceRunId,
		{
			refetchInterval: (query) =>
				ACTIVE_RUN_STATUSES.has(query.state.data?.status ?? "")
					? 2_000
					: false,
		},
	);
	const selectedSource = rawSelectedSource as unknown as
		AgentRunDetailResponse | undefined;
	const selectedSourceActivity = useMemo(
		() =>
			selectedSource
				? buildRunActivity(
						selectedSource.steps,
						selectedSource.child_run_ids,
						selectedSource.child_runs,
					)
				: [],
		[selectedSource],
	);
	const selectedActivity =
		(selectedSnapshot?.sourceRunId
			? selectedSourceActivity
			: activity
		).find((item) => item.id === selectedActivityId) ??
		(selectedSnapshot?.item.id === selectedActivityId
			? selectedSnapshot.item
			: null);
	useEffect(() => {
		onInspectionChange?.(!!selectedActivity);
	}, [onInspectionChange, selectedActivity]);
	const handleSelectActivity = (
		item: RunActivityItem,
		sourceRunId?: string,
	) => {
		inspectionTrigger.current =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;
		if (item.id === restoreActivityId) setRestoredActivity(item.id);
		setSelectedActivityId(item.id);
		setSelectedSnapshot({ item, sourceRunId });
	};

	if (!activity.length) {
		return (
			<div>
				<div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
					{toolbarLeading}
					{toolbarActions}
				</div>
				<div
					data-slot="activity-empty-state"
					className="rounded-[var(--bf-radius-feature)] border border-dashed border-border/70 bg-muted/30 px-4 py-6 text-center"
				>
					<p className="text-sm font-medium leading-6">
						No activity to summarize
					</p>
					<p className="mt-1 text-sm leading-6 text-muted-foreground">
						Any recorded executor steps are still available in
						Advanced.
					</p>
				</div>
			</div>
		);
	}

	const expandableActivityIds = activity
		.filter((item) => item.kind === "delegation" && !!item.childRunId)
		.map((item) => item.id);

	return (
		<div
			className={cn(
				"flex min-w-0 flex-col",
				!inlineInspector && "gap-3",
				inlineInspector && "min-h-0 flex-1",
			)}
			onKeyDown={(event) => {
				if (
					inlineInspector &&
					selectedActivity &&
					event.key === "Escape"
				) {
					event.preventDefault();
					setSelectedActivityId(null);
					inspectionTrigger.current?.focus({ preventScroll: true });
				}
			}}
		>
			{(toolbarLeading ||
				expandableActivityIds.length > 0 ||
				toolbarActions) && (
				<div
					data-slot="activity-toolbar"
					className={cn(
						"flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border/60",
						inlineInspector ? "px-4 py-3" : "pb-2",
					)}
				>
					<div className="flex min-w-0 flex-wrap items-center gap-2">
						{toolbarLeading}
						{expandableActivityIds.length ? (
							<>
								<Button
									type="button"
									variant="ghost"
									className="min-h-11 px-2 text-xs text-muted-foreground hover:text-foreground"
									onClick={() => {
										setBulkExpansionRequest((current) => ({
											expanded: true,
											token: (current?.token ?? 0) + 1,
										}));
									}}
								>
									Expand all
								</Button>
								<Button
									type="button"
									variant="ghost"
									className="min-h-11 px-2 text-xs text-muted-foreground hover:text-foreground"
									onClick={() => {
										setBulkExpansionRequest((current) => ({
											expanded: false,
											token: (current?.token ?? 0) + 1,
										}));
									}}
								>
									Collapse all
								</Button>
							</>
						) : null}
					</div>
					{toolbarActions}
				</div>
			)}
			<div
				className={cn(
					"flex min-w-0 items-start",
					inlineInspector && "min-h-0 flex-1 items-stretch",
				)}
			>
				<div
					className={cn(
						"min-w-0 flex-1",
						inlineInspector &&
							"min-h-0 overflow-y-auto overflow-x-hidden",
						!inlineInspector && "max-w-2xl",
					)}
					role="region"
					aria-label="Activity calls"
				>
					<ol aria-label="Run activity" className="space-y-1 pb-2">
						{activity.map((item) => (
							<ActivityTreeRow
								key={`${item.id}:${bulkExpansionRequest?.token ?? 0}`}
								item={item}
								depth={depth}
								rowDepth={0}
								runStatus={runStatus}
								highlighted={item.id === highlightedActivityId}
								selected={item.id === selectedActivityId}
								selectedActivityId={selectedActivityId}
								onSelect={handleSelectActivity}
								bulkExpansionRequest={bulkExpansionRequest}
								expandedDelegationIds={expandedDelegationIds}
								onDelegationExpandedChange={
									onDelegationExpandedChange
								}
								restoreActivityId={
									restoredActivity === restoreActivityId
										? null
										: restoreActivityId
								}
								joinedRows={joinedRows}
								onOpenChildRun={onOpenChildRun}
								childRunOrigin={childRunOrigin}
							/>
						))}
					</ol>
				</div>
				{inlineInspector ? (
					<AnimatePresence initial={false}>
						{selectedActivity && (
							<motion.aside
								key="call-inspector"
								role="complementary"
								initial={{
									width: 0,
									opacity: 0,
									marginLeft: 0,
								}}
								animate={{
									width: "52%",
									opacity: 1,
									marginLeft: 0,
								}}
								exit={{ width: 0, opacity: 0, marginLeft: 0 }}
								transition={{
									duration: reducedMotion ? 0 : 0.24,
									ease: [0.22, 1, 0.36, 1],
								}}
								className="flex min-h-0 shrink-0 flex-col overflow-hidden border-l bg-muted/20 motion-reduce:transition-none"
								aria-label="Call inspector"
							>
								<div className="flex min-h-0 min-w-80 flex-1 flex-col">
									<ActivityDetailPanel
										item={selectedActivity}
										childRunOrigin={childRunOrigin}
										onOpenChildRun={onOpenChildRun}
										onClose={() => {
											setSelectedActivityId(null);
											inspectionTrigger.current?.focus({
												preventScroll: true,
											});
										}}
									/>
								</div>
							</motion.aside>
						)}
					</AnimatePresence>
				) : (
					<Sheet
						modal={compactInspector}
						open={!!selectedActivity}
						onOpenChange={(open) => {
							if (!open) setSelectedActivityId(null);
						}}
					>
						{selectedSnapshot && (
							<SheetContent
								aria-describedby={undefined}
								className="w-full overflow-hidden sm:max-w-xl"
								onInteractOutside={(event) => {
									if (!compactInspector)
										event.preventDefault();
								}}
								onCloseAutoFocus={(event) => {
									event.preventDefault();
									if (inspectionTrigger.current?.isConnected)
										inspectionTrigger.current.focus({
											preventScroll: true,
										});
								}}
							>
								<ActivityDetailPanel
									item={
										selectedActivity ??
										selectedSnapshot.item
									}
									childRunOrigin={childRunOrigin}
									onOpenChildRun={onOpenChildRun}
								/>
							</SheetContent>
						)}
					</Sheet>
				)}
			</div>
		</div>
	);
}

function ActivityTreeRow({
	item,
	sourceRunId,
	depth,
	rowDepth,
	runStatus,
	highlighted,
	selected,
	selectedActivityId,
	onSelect,
	bulkExpansionRequest,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId,
	joinedRows,
	onOpenChildRun,
	childRunOrigin,
}: {
	item: RunActivityItem;
	sourceRunId?: string;
	depth: number;
	rowDepth: number;
	runStatus?: string | null;
	highlighted: boolean;
	selected: boolean;
	selectedActivityId: string | null;
	onSelect: (item: RunActivityItem, sourceRunId?: string) => void;
	bulkExpansionRequest: BulkExpansionRequest;
	expandedDelegationIds?: ReadonlySet<string>;
	onDelegationExpandedChange?: (
		activityId: string,
		expanded: boolean,
	) => void;
	restoreActivityId?: string | null;
	joinedRows?: boolean;
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
}) {
	const [localOpen, setLocalOpen] = useState(
		() => bulkExpansionRequest?.expanded ?? false,
	);
	const labelId = useId();
	const rowRef = useRef<HTMLLIElement>(null);
	const lastRestoreActivityId = useRef<string | null>(null);
	const lastBulkToken = useRef<number | null>(null);
	const expandable =
		item.kind === "delegation" && !!item.childRunId && depth < 4;
	const open =
		expandedDelegationIds !== undefined
			? expandedDelegationIds.has(item.id)
			: localOpen;

	useEffect(() => {
		if (!expandable || !bulkExpansionRequest || !onDelegationExpandedChange)
			return;
		if (lastBulkToken.current === bulkExpansionRequest.token) return;
		lastBulkToken.current = bulkExpansionRequest.token;
		onDelegationExpandedChange(item.id, bulkExpansionRequest.expanded);
	}, [bulkExpansionRequest, expandable, item.id, onDelegationExpandedChange]);

	useEffect(() => {
		if (restoreActivityId !== item.id) return;
		if (lastRestoreActivityId.current === restoreActivityId) return;
		lastRestoreActivityId.current = restoreActivityId;
		if (selectedActivityId !== item.id) {
			onSelect(item, sourceRunId);
		}
		rowRef.current?.scrollIntoView({ behavior: "auto", block: "center" });
	}, [
		item,
		item.id,
		onSelect,
		restoreActivityId,
		selectedActivityId,
		sourceRunId,
	]);

	function toggleOpen() {
		if (!expandable) return;
		const nextOpen = !open;
		if (onDelegationExpandedChange) {
			onDelegationExpandedChange(item.id, nextOpen);
			return;
		}
		setLocalOpen(nextOpen);
	}

	const {
		data: rawChild,
		isLoading,
		isError,
		isFetching,
		refetch,
	} = useAgentRun(open ? (item.childRunId ?? undefined) : undefined, {
		refetchInterval: (query) =>
			ACTIVE_RUN_STATUSES.has(query.state.data?.status ?? "")
				? 2_000
				: false,
	});
	const child = rawChild as unknown as AgentRunDetailResponse | undefined;
	const { data: workflowExecution } = useExecution(
		item.executionId ?? undefined,
	);
	const agentName = child?.agent_name ?? item.agentName;
	const title =
		item.kind === "delegation"
			? (agentName ?? "Delegated agent")
			: item.executionId
				? (workflowExecution?.workflow_name ??
					item.toolName ??
					item.title)
				: item.title;
	const childStatus = child?.status ?? item.childStatus;
	const failed =
		item.isError ||
		item.kind === "error" ||
		(childStatus ? isFailedRunStatus(childStatus) : false);
	const status =
		childStatus ??
		(failed ? "failed" : item.resultStep ? "completed" : null);
	const statusId = status ? `${labelId}-status` : undefined;
	const childActivity = useMemo(
		() =>
			child
				? buildRunActivity(
						child.steps,
						child.child_run_ids,
						child.child_runs,
					)
				: [],
		[child],
	);

	const Icon =
		item.kind === "delegation"
			? GitBranch
			: item.kind === "response"
				? MessageSquareText
				: failed
					? AlertCircle
					: item.executionId
						? Workflow
						: Check;
	const rowType =
		item.kind === "delegation"
			? "Agent"
			: item.executionId
				? "Workflow"
				: item.kind === "response"
					? "Response"
					: "Action";
	const caption =
		item.kind === "response" ? null : (item.task ?? item.description);

	return (
		<li
			ref={rowRef}
			id={activityDomId(item.id)}
			tabIndex={-1}
			className={cn(
				"relative scroll-mt-24 outline-none [overflow-wrap:anywhere]",
				rowDepth > 0 &&
					"before:pointer-events-none before:absolute before:inset-y-0 before:start-0 before:z-10 before:w-px before:bg-border/70 last:before:bottom-auto last:before:h-[30px] after:pointer-events-none after:absolute after:start-0 after:top-[30px] after:z-10 after:h-px after:w-3 after:bg-border/70",
				selected && "before:opacity-0 after:opacity-0",
			)}
			data-activity-id={item.id}
			data-activity-kind={item.kind}
			data-highlighted={highlighted ? "true" : "false"}
		>
			<div
				className={cn(
					"relative min-w-0 rounded-[var(--bf-radius-control)] px-2 py-3 transition-colors motion-reduce:transition-none",
					rowDepth > 0 && "ps-4",
					(joinedRows || rowDepth > 0) && "rounded-none",
					selected
						? "bg-[var(--bf-info-soft)]/55 hover:bg-[var(--bf-info-soft)]/55"
						: "hover:bg-muted/35",
					highlighted && "ring-2 ring-inset ring-[var(--bf-info)]/45",
				)}
			>
				<div className="flex min-w-0 items-start gap-1">
					<button
						type="button"
						onClick={toggleOpen}
						disabled={!expandable}
						aria-expanded={expandable ? open : undefined}
						aria-label={
							expandable
								? `${open ? "Hide" : "Show"} details for ${title}`
								: undefined
						}
						aria-describedby={statusId}
						className={cn(
							"mt-0.5 grid size-8 shrink-0 place-items-center rounded-[var(--bf-radius-control)] text-muted-foreground",
							expandable &&
								"hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
						)}
					>
						{isLoading && open ? (
							<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						) : (
							<ChevronRight
								className={cn(
									"size-4 transition-transform motion-reduce:transition-none",
									open && "rotate-90",
									!expandable && "opacity-0",
								)}
							/>
						)}
					</button>
					<button
						type="button"
						aria-description={rowType}
						aria-pressed={selected}
						aria-labelledby={`${labelId}-title${caption ? ` ${labelId}-caption` : ""}`}
						aria-describedby={statusId}
						onClick={() => onSelect(item, sourceRunId)}
						className="flex min-w-0 flex-1 items-start gap-3 rounded-[var(--bf-radius-control)] text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						<span
							className={cn(
								"grid size-9 shrink-0 place-items-center rounded-full border",
								failed
									? "border-[var(--bf-danger)]/25 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
									: item.kind === "delegation"
										? "border-[var(--bf-info)]/25 bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
										: "border-[var(--bf-success)]/25 bg-[var(--bf-success-soft)] text-[var(--bf-success)]",
							)}
						>
							<Icon className="size-4" aria-hidden="true" />
						</span>
						<span className="min-w-0 flex-1">
							<span
								id={`${labelId}-title`}
								className="block break-words text-sm font-medium leading-5"
							>
								{title}
							</span>
							{caption ? (
								<span
									id={`${labelId}-caption`}
									className="mt-0.5 line-clamp-2 break-words text-xs leading-5 text-muted-foreground"
								>
									{caption && (
										<MarkdownContent
											content={caption}
											variant="preview"
										/>
									)}
								</span>
							) : null}
							<span className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
								{status ? (
									<DelegationStatusBadge
										id={statusId}
										status={status}
									/>
								) : (
									<span>
										{runStatus === "running"
											? "In progress"
											: "No status"}
									</span>
								)}
								<span aria-hidden="true">·</span>
								<span className="tabular-nums">
									{item.durationMs != null
										? formatDuration(item.durationMs)
										: "—"}
								</span>
							</span>
						</span>
					</button>
				</div>
			</div>
			{isError ? (
				<div
					role="alert"
					className="mx-3 mb-2 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-3 text-sm"
				>
					<p>
						Could not {child ? "refresh" : "load"} delegated run
						details.
						{child
							? " Previously loaded details are still shown."
							: ""}
					</p>
					<Button
						variant="outline"
						className="mt-2 min-h-11"
						disabled={isFetching}
						onClick={() => void refetch()}
					>
						Retry delegated run
					</Button>
				</div>
			) : null}
			{open && childActivity.length ? (
				<ol
					className={cn(
						"space-y-0",
						rowDepth === 0 ? "ms-6" : "ms-8",
					)}
				>
					{childActivity.map((childItem) => (
						<ActivityTreeRow
							key={`${childItem.id}:${bulkExpansionRequest?.token ?? 0}`}
							item={childItem}
							sourceRunId={item.childRunId ?? undefined}
							depth={depth + 1}
							rowDepth={rowDepth + 1}
							runStatus={child?.status}
							highlighted={false}
							selected={childItem.id === selectedActivityId}
							selectedActivityId={selectedActivityId}
							onSelect={onSelect}
							bulkExpansionRequest={bulkExpansionRequest}
							expandedDelegationIds={expandedDelegationIds}
							onDelegationExpandedChange={
								onDelegationExpandedChange
							}
							restoreActivityId={restoreActivityId}
							joinedRows={joinedRows}
							onOpenChildRun={onOpenChildRun}
							childRunOrigin={childRunOrigin}
						/>
					))}
				</ol>
			) : open && isLoading ? (
				<div className="flex items-center gap-2 border-t px-14 py-3 text-sm leading-6 text-muted-foreground">
					<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
					Loading delegated work…
				</div>
			) : null}
		</li>
	);
}

function ActivityDetailPanel({
	onClose,
	item,
	childRunOrigin,
	onOpenChildRun,
}: {
	onClose?: () => void;
	item: RunActivityItem;
	childRunOrigin?: AgentRunNavigationOrigin;
	onOpenChildRun?: (activityId: string) => void;
}) {
	const {
		data: rawChild,
		isLoading,
		isError,
		isFetching,
		refetch,
	} = useAgentRun(
		item.kind === "delegation" ? (item.childRunId ?? undefined) : undefined,
		{
			refetchInterval: (query) =>
				ACTIVE_RUN_STATUSES.has(query.state.data?.status ?? "")
					? 2_000
					: false,
		},
	);
	const child = rawChild as unknown as AgentRunDetailResponse | undefined;
	const { data: execution } = useExecution(item.executionId ?? undefined);
	const title =
		execution?.workflow_name ??
		child?.agent_name ??
		item.agentName ??
		(item.executionId ? item.toolName : null) ??
		item.title;
	const childAgentId = child?.agent_id ?? item.childAgentId;
	const childActivity = useMemo(
		() =>
			child
				? buildRunActivity(
						child.steps,
						child.child_run_ids,
						child.child_runs,
					)
				: [],
		[child],
	);
	const childActivityReferences = useMemo(
		() => buildActivityReferenceIndex(childActivity),
		[childActivity],
	);
	const inputDetail = activityInputDetail(item, child);
	const outputDetail =
		execution?.result !== undefined && execution.result !== null
			? renderDetail(execution.result)
			: activityOutputDetail(item, child);
	const usage = child?.ai_usage ?? [];
	const hasUsage = usage.length > 0 || !!child?.ai_totals;
	const overviewOutcome = child?.did ?? child?.answered ?? item.description;
	const isDelegation = item.kind === "delegation";
	const tabs = [
		["overview", "Overview", isDelegation],
		["output", item.kind === "response" ? "Response" : "Result", true],
		["input", "Input", !!inputDetail],
		["usage", "Usage", hasUsage],
	] as const;

	return (
		<section
			className="flex min-h-0 flex-1 flex-col"
			aria-label="Selected call details"
		>
			{onClose ? (
				<header className="flex min-h-16 shrink-0 items-start justify-between gap-3 border-b border-border/60 px-5 py-3">
					<h3 className="min-w-0 pt-1 text-sm font-semibold [overflow-wrap:anywhere]">
						{title}
					</h3>
					<Button
						size="icon"
						variant="ghost"
						aria-label="Close call details"
						onClick={onClose}
						className="shrink-0"
					>
						<X className="size-4" />
					</Button>
				</header>
			) : (
				<SheetHeader className="border-b border-border">
					<SheetTitle>{title}</SheetTitle>
				</SheetHeader>
			)}
			<div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-2">
				<div className="flex shrink-0 flex-wrap items-center gap-2">
					{item.executionId ? (
						<Link
							to={`/history/${item.executionId}`}
							onClick={() => onOpenChildRun?.(item.id)}
							className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-0 text-xs font-medium text-primary hover:bg-[var(--bf-info-soft)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							View execution
							<ArrowUpRight className="size-4" />
						</Link>
					) : null}
					{childAgentId && item.childRunId ? (
						<Link
							to={`/agents/${childAgentId}/runs/${item.childRunId}`}
							state={
								childRunOrigin
									? createAgentRunNavigationState(
											childRunOrigin,
										)
									: undefined
							}
							onClick={() => onOpenChildRun?.(item.id)}
							className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-0 text-xs font-medium text-primary hover:bg-[var(--bf-info-soft)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							Open run
							<ArrowUpRight className="size-4" />
						</Link>
					) : null}
				</div>
				{isError ? (
					<div
						role="alert"
						className="mt-3 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-3 text-sm"
					>
						<p>
							Could not {child ? "refresh" : "load"} selected
							delegated run details.
							{child
								? " Previously loaded details are still shown."
								: ""}
						</p>
						<Button
							className="mt-2 min-h-11"
							variant="outline"
							disabled={isFetching}
							onClick={() => void refetch()}
						>
							Retry delegated run
						</Button>
					</div>
				) : null}
				{isLoading ? (
					<div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
						<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						Loading selected delegated run…
					</div>
				) : null}
				<Tabs
					key={item.id}
					defaultValue={isDelegation ? "overview" : "output"}
					className="mt-1 min-w-0 gap-3"
				>
					<TabsList
						variant="line"
						className="flex min-h-11 max-w-full justify-start overflow-x-auto"
						aria-label="Selected call detail sections"
					>
						{tabs
							.filter(([, , enabled]) => enabled)
							.map(([value, label]) => (
								<TabsTrigger
									key={value}
									value={value}
									className="min-h-11 shrink-0 px-2 sm:px-3"
								>
									{label}
								</TabsTrigger>
							))}
					</TabsList>
					<TabsContent value="overview" className="mt-0 min-w-0">
						<div className="grid gap-5">
							<OverviewBlock label="Task">
								<MarkdownContent
									content={
										child?.asked ??
										item.task ??
										"No task summary recorded."
									}
								/>
							</OverviewBlock>
							<OverviewBlock label="Outcome">
								<DidNarrative
									text={overviewOutcome}
									activityReferences={childActivityReferences}
									fallback={<>No outcome summary recorded.</>}
								/>
							</OverviewBlock>
						</div>
					</TabsContent>
					<TabsContent value="input" className="mt-0 min-w-0">
						{inputDetail ? (
							<DetailBlock detail={inputDetail} />
						) : null}
					</TabsContent>
					<TabsContent value="output" className="mt-0 min-w-0">
						{outputDetail ? (
							<DetailBlock detail={outputDetail} />
						) : (
							<p className="text-sm text-muted-foreground">
								No output recorded.
							</p>
						)}
					</TabsContent>
					<TabsContent value="usage" className="mt-0 min-w-0">
						{hasUsage ? (
							<SelectedUsage
								usage={usage}
								totals={child?.ai_totals ?? null}
							/>
						) : (
							<p className="text-sm text-muted-foreground">
								No usage recorded for this selected call.
							</p>
						)}
					</TabsContent>
				</Tabs>
			</div>
		</section>
	);
}

function activityInputDetail(
	item: RunActivityItem,
	child: AgentRunDetailResponse | undefined,
): DetailRender | null {
	if (child && !isEmptyJson(child.input)) return renderDetail(child.input);
	const callContent = (item.callStep?.content ?? {}) as Record<
		string,
		unknown
	>;
	return renderDetail(callContent.arguments);
}

function activityOutputDetail(
	item: RunActivityItem,
	child: AgentRunDetailResponse | undefined,
): DetailRender | null {
	if (child && !isEmptyJson(child.output)) return renderDetail(child.output);
	const resultContent = (item.resultStep?.content ?? {}) as Record<
		string,
		unknown
	>;
	const resultValue =
		item.resultStep?.type === "llm_response"
			? resultContent.content
			: item.isError
				? (resultContent.error ?? resultContent.result ?? resultContent)
				: (resultContent.result ??
					(item.resultStep && !item.toolName ? resultContent : null));
	return renderDetail(resultValue);
}

function OverviewBlock({
	label,
	children,
}: {
	label: string;
	children: React.ReactNode;
}) {
	return (
		<section className="grid gap-1.5">
			<div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
				{label}
			</div>
			<div className="text-sm leading-6">{children}</div>
		</section>
	);
}

function SelectedUsage({
	usage,
	totals,
}: {
	usage: NonNullable<AgentRunDetailResponse["ai_usage"]>;
	totals: AgentRunDetailResponse["ai_totals"] | null;
}) {
	return (
		<div className="grid gap-3">
			{usage.map((entry, index) => (
				<dl
					key={`${entry.model}-${index}`}
					className="grid gap-x-4 gap-y-2 rounded-[var(--bf-radius-feature)] border border-border/70 bg-muted/35 p-3 text-xs sm:grid-cols-4"
				>
					<UsageMetric label="Model" value={entry.model} />
					<UsageMetric
						label="Input"
						value={formatNumber(entry.input_tokens)}
					/>
					<UsageMetric
						label="Output"
						value={formatNumber(entry.output_tokens)}
					/>
					<UsageMetric label="Cost" value={formatCost(entry.cost)} />
				</dl>
			))}
			{totals ? (
				<dl className="grid gap-x-4 gap-y-2 border-t pt-3 text-xs sm:grid-cols-4">
					<UsageMetric
						label="Calls"
						value={formatNumber(totals.call_count)}
					/>
					<UsageMetric
						label="Input"
						value={formatNumber(totals.total_input_tokens)}
					/>
					<UsageMetric
						label="Output"
						value={formatNumber(totals.total_output_tokens)}
					/>
					<UsageMetric
						label="Cost"
						value={formatCost(totals.total_cost)}
					/>
				</dl>
			) : null}
		</div>
	);
}

function UsageMetric({ label, value }: { label: string; value: string }) {
	return (
		<div className="min-w-0">
			<dt className="text-muted-foreground">{label}</dt>
			<dd className="mt-1 break-words font-mono tabular-nums">{value}</dd>
		</div>
	);
}

function DelegationStatusBadge({
	id,
	status,
}: {
	id: string | undefined;
	status: string;
}) {
	const label = runStatusLabel(status);
	const failed = isFailedRunStatus(status);
	const active = ACTIVE_RUN_STATUSES.has(status);
	const completed = status === "completed";
	const StatusIcon = failed
		? AlertCircle
		: status === "running" || status === "cancelling"
			? Loader2
			: completed
				? Check
				: CircleDot;

	return (
		<span
			id={id}
			aria-label={`Delegated run status: ${label}`}
			className={cn(
				"inline-flex min-h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-medium",
				failed
					? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
					: active
						? "bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
						: completed
							? "bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
							: "bg-muted text-muted-foreground",
			)}
		>
			<StatusIcon
				aria-hidden="true"
				className={cn(
					"h-3 w-3",
					(status === "running" || status === "cancelling") &&
						"animate-spin motion-reduce:animate-none",
				)}
			/>
			{label}
		</span>
	);
}

function isFailedRunStatus(status: string): boolean {
	return [
		"failed",
		"budget_exceeded",
		"cancelled",
		"timeout",
		"timed_out",
	].includes(status);
}

function runStatusLabel(status: string): string {
	switch (status) {
		case "queued":
			return "Queued";
		case "running":
			return "Running";
		case "cancelling":
			return "Cancelling";
		case "cancelled":
			return "Cancelled";
		case "failed":
			return "Failed";
		case "budget_exceeded":
			return "Budget exceeded";
		case "timeout":
		case "timed_out":
			return "Timed out";
		case "completed":
			return "Completed";
		default:
			return status.replace(/_/g, " ");
	}
}

type DetailRender =
	{ kind: "json"; value: unknown } | { kind: "text"; value: string };

interface StepViewModel {
	icon: typeof Wrench;
	iconClass: string;
	label: string;
	summary: string | null;
	primaryDetail: DetailRender | null;
	secondaryDetail: (DetailRender & { label: string }) | null;
}

function buildViewModel(step: AgentRunStepResponse): StepViewModel {
	const c = (step.content ?? {}) as Record<string, unknown>;
	const type = step.type ?? "step";

	switch (type) {
		case "tool_call": {
			const name = (c.tool_name as string) || "tool";
			const args = c.arguments;
			return {
				icon: Wrench,
				iconClass: "bg-[var(--bf-info-soft)] text-[var(--bf-info)]",
				label: `Called ${name}`,
				summary: null,
				primaryDetail: isEmptyJson(args)
					? null
					: { kind: "json", value: args },
				secondaryDetail: null,
			};
		}
		case "tool_result": {
			const name = (c.tool_name as string) || "tool";
			const result = c.result;
			return {
				icon: CircleDot,
				iconClass:
					"bg-[var(--bf-success-soft)] text-[var(--bf-success)]",
				label: `Result from ${name}`,
				summary: inlineTextPreview(result, 100),
				primaryDetail: renderDetail(result),
				secondaryDetail: null,
			};
		}
		case "tool_error": {
			const name = (c.tool_name as string) || "tool";
			const error = c.error ?? c.result;
			return {
				icon: AlertCircle,
				iconClass: "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]",
				label: `Error from ${name}`,
				summary: inlineTextPreview(error, 100),
				primaryDetail: renderDetail(error),
				secondaryDetail: null,
			};
		}
		case "llm_request": {
			const model = (c.model as string | null) ?? null;
			const tools = (c.tools_count as number | undefined) ?? null;
			const messages = (c.messages_count as number | undefined) ?? null;
			const bits: string[] = [];
			if (model) bits.push(model);
			if (messages != null) bits.push(`${messages} msgs`);
			if (tools != null) bits.push(`${tools} tools`);
			return {
				icon: Cpu,
				iconClass: "bg-muted text-muted-foreground",
				label: "LLM request",
				summary: bits.length ? bits.join(" · ") : null,
				primaryDetail: { kind: "json", value: c },
				secondaryDetail: null,
			};
		}
		case "llm_response": {
			const text = (c.content as string | undefined) ?? "";
			const toolCalls =
				(c.tool_calls as
					| Array<{
							name?: string;
					  }>
					| undefined) ?? [];
			const callNames = toolCalls
				.map((tc) => tc.name)
				.filter(Boolean) as string[];
			// Label: when the LLM picked tools, name them directly.
			// "Decided to call get_ticket, send_email" beats the abstract
			// "LLM decided to call tools" by one click of comprehension.
			const label =
				callNames.length > 0
					? `Decided to call ${callNames.join(", ")}`
					: text
						? "Reasoned"
						: "LLM response";
			return {
				icon: Bot,
				iconClass: "bg-[var(--bf-info-soft)] text-[var(--bf-info)]",
				label,
				// If we put the names in the label, no summary needed; show the
				// reasoning text as summary when it's the standalone case.
				summary:
					callNames.length > 0 ? null : inlineTextPreview(text, 120),
				primaryDetail: text ? { kind: "text", value: text } : null,
				secondaryDetail:
					callNames.length > 0
						? {
								kind: "json",
								label: "Tool calls",
								value: toolCalls,
							}
						: null,
			};
		}
		case "error":
		case "budget_warning":
		case "cancelled": {
			return {
				icon: AlertCircle,
				iconClass:
					type === "error"
						? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
						: "bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]",
				label:
					type === "cancelled"
						? "Cancelled"
						: type === "budget_warning"
							? "Budget warning"
							: "Error",
				summary: errorSummary(c),
				primaryDetail: { kind: "json", value: c },
				secondaryDetail: null,
			};
		}
		default: {
			return {
				icon: MessageSquare,
				iconClass: "bg-muted text-muted-foreground",
				label: type,
				summary: null,
				primaryDetail: { kind: "json", value: c },
				secondaryDetail: null,
			};
		}
	}
}

function renderDetail(value: unknown): DetailRender | null {
	if (value === null || value === undefined || value === "") return null;
	return typeof value === "string"
		? { kind: "text", value }
		: { kind: "json", value };
}

function inlineTextPreview(value: unknown, maxLength: number): string | null {
	if (typeof value !== "string") return null;
	const trimmed = value.trim();
	if (!trimmed || looksStructured(trimmed)) return null;
	return truncate(trimmed, maxLength);
}

function errorSummary(content: Record<string, unknown>): string | null {
	for (const key of ["message", "error", "reason"]) {
		const preview = inlineTextPreview(content[key], 120);
		if (preview) return preview;
	}
	return null;
}

function truncate(s: string, n: number): string {
	if (s.length <= n) return s;
	return s.slice(0, n - 1) + "…";
}

export interface AdvancedTimelineProps {
	steps: AgentRunStepResponse[] | null | undefined;
}

export function AdvancedTimeline({ steps }: AdvancedTimelineProps) {
	if (!steps || !steps.length) {
		return (
			<p className="text-sm leading-6 text-muted-foreground">
				No steps recorded.
			</p>
		);
	}
	return (
		<ol className="flex min-w-0 flex-col gap-1.5">
			{steps.map((step, i) => (
				<TimelineRow key={step.id ?? i} step={step} index={i + 1} />
			))}
		</ol>
	);
}

function TimelineRow({
	step,
	index,
}: {
	step: AgentRunStepResponse;
	index: number;
}) {
	const [open, setOpen] = useState(false);
	const vm = buildViewModel(step);
	const hasDetail = !!vm.primaryDetail || !!vm.secondaryDetail;
	const Icon = vm.icon;
	return (
		<li className="min-w-0 overflow-hidden rounded-xl border border-border/70 bg-muted/50">
			<button
				type="button"
				onClick={() => hasDetail && setOpen((v) => !v)}
				disabled={!hasDetail}
				aria-expanded={open}
				aria-label={
					hasDetail ? `Toggle details for step ${index}` : undefined
				}
				className={cn(
					"flex min-h-11 min-w-0 w-full items-start gap-2 px-3 py-3 text-left text-sm leading-6",
					hasDetail &&
						"hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
				)}
			>
				<div
					className={cn(
						"mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full",
						vm.iconClass,
					)}
				>
					<Icon className="h-3.5 w-3.5" />
				</div>
				<div className="min-w-0 flex-1">
					<div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1">
						<span
							className="min-w-0 break-words font-medium"
							title={vm.label}
						>
							{vm.label}
						</span>
						{vm.summary ? (
							<span className="break-words text-muted-foreground">
								{vm.summary}
							</span>
						) : null}
					</div>
				</div>
				<span className="ml-auto flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
					{step.tokens_used ? (
						<span title="Tokens used">
							{formatNumber(step.tokens_used)} tok
						</span>
					) : null}
					{step.duration_ms != null ? (
						<span>{formatDuration(step.duration_ms)}</span>
					) : null}
					<span className="font-mono">#{index}</span>
					{hasDetail ? (
						<ChevronRight
							className={cn(
								"h-4 w-4 transition-transform motion-reduce:transition-none",
								open && "rotate-90",
							)}
						/>
					) : null}
				</span>
			</button>
			{open && hasDetail ? (
				<div className="border-t border-border/70 px-3 py-3">
					{vm.primaryDetail ? (
						<DetailBlock detail={vm.primaryDetail} />
					) : null}
					{vm.secondaryDetail ? (
						<div className="mt-2">
							<div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
								{vm.secondaryDetail.label}
							</div>
							<DetailBlock detail={vm.secondaryDetail} />
						</div>
					) : null}
				</div>
			) : null}
		</li>
	);
}

function DetailBlock({ detail }: { detail: DetailRender }) {
	if (detail.kind === "json") {
		return (
			<div className="min-w-0">
				<VariablesTreeView data={asVariableRecord(detail.value)} />
			</div>
		);
	}
	const parsed = tryParseJson(detail.value);
	if (parsed !== UNPARSEABLE) {
		return (
			<div className="min-w-0">
				<VariablesTreeView data={asVariableRecord(parsed)} />
			</div>
		);
	}
	return <MarkdownContent content={detail.value} />;
}

function asVariableRecord(value: unknown): Record<string, unknown> {
	if (value !== null && typeof value === "object" && !Array.isArray(value)) {
		return value as Record<string, unknown>;
	}
	return { value };
}

function looksStructured(value: string): boolean {
	return (
		(value.startsWith("{") && value.endsWith("}")) ||
		(value.startsWith("[") && value.endsWith("]"))
	);
}

const UNPARSEABLE = Symbol("unparseable");
function tryParseJson(value: string): unknown {
	const trimmed = value.trim();
	if (!looksStructured(trimmed)) {
		return UNPARSEABLE;
	}
	try {
		return JSON.parse(trimmed);
	} catch {
		return UNPARSEABLE;
	}
}
