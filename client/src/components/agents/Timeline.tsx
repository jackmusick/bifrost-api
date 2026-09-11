import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
/**
 * Timeline has two deliberately different projections of a run:
 *
 * - Timeline: a user-facing activity story. It groups the executor's
 *   decision/call/result records into one operation and nests child runs.
 * - AdvancedTimeline: the exact step sequence with raw payload disclosure.
 */

import { useEffect, useMemo, useRef, useState } from "react";
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
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
	/** Used only to keep pathological/cyclic history from nesting forever. */
	depth?: number;
}

export function Timeline({
	steps,
	childRunIds = EMPTY_CHILD_RUN_IDS,
	childRuns = EMPTY_CHILD_RUNS,
	runStatus,
	highlightedActivityId = null,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId = null,
	onOpenChildRun,
	childRunOrigin,
	depth = 0,
}: TimelineProps) {
	const activity = useMemo(
		() => buildRunActivity(steps, childRunIds, childRuns),
		[steps, childRunIds, childRuns],
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
	const handleSelectActivity = (
		item: RunActivityItem,
		sourceRunId?: string,
	) => {
		setSelectedActivityId(item.id);
		setSelectedSnapshot({ item, sourceRunId });
	};

	if (!activity.length) {
		return (
			<div className="rounded-[var(--bf-radius-feature)] border border-dashed border-border/70 bg-muted/30 px-4 py-6 text-center">
				<p className="text-sm font-medium leading-6">
					No activity to summarize
				</p>
				<p className="mt-1 text-sm leading-6 text-muted-foreground">
					Any recorded executor steps are still available in Advanced.
				</p>
			</div>
		);
	}

	const expandableActivityIds = activity
		.filter((item) => item.kind === "delegation" && !!item.childRunId)
		.map((item) => item.id);

	return (
		<div className="grid min-w-0 gap-5">
			{expandableActivityIds.length ? (
				<div className="flex flex-wrap items-center gap-2">
					<Button
						type="button"
						variant="ghost"
						className="min-h-11 px-2 text-primary"
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
						className="min-h-11 px-2 text-primary"
						onClick={() => {
							setBulkExpansionRequest((current) => ({
								expanded: false,
								token: (current?.token ?? 0) + 1,
							}));
						}}
					>
						Collapse all
					</Button>
				</div>
			) : null}
			<div className="min-w-0 overflow-hidden rounded-[var(--bf-radius-feature)] border border-border/70">
				<div className="hidden grid-cols-[minmax(0,1fr)_5rem_6rem_4rem] gap-3 border-b bg-muted/35 px-3 py-2 text-xs font-medium text-muted-foreground md:grid">
					<div>Name</div>
					<div>Type</div>
					<div>Status</div>
					<div>Duration</div>
				</div>
				<ol
					aria-label="Run activity"
					className="divide-y divide-border/70"
				>
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
							restoreActivityId={restoreActivityId}
							onOpenChildRun={onOpenChildRun}
							childRunOrigin={childRunOrigin}
						/>
					))}
				</ol>
			</div>
			{selectedActivity ? (
				<ActivityDetailPanel
					item={selectedActivity}
					childRunOrigin={childRunOrigin}
					onOpenChildRun={onOpenChildRun}
				/>
			) : null}
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
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
}) {
	const [localOpen, setLocalOpen] = useState(
		() => bulkExpansionRequest?.expanded ?? false,
	);
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
	const agentName = child?.agent_name ?? item.agentName;
	const title =
		item.kind === "delegation"
			? (agentName ?? "Delegated agent")
			: item.title;
	const childStatus = child?.status ?? item.childStatus;
	const failed =
		item.isError ||
		item.kind === "error" ||
		(childStatus ? isFailedRunStatus(childStatus) : false);
	const status =
		childStatus ??
		(failed ? "failed" : item.resultStep ? "completed" : null);
	const statusId = status ? `${activityDomId(item.id)}-status` : undefined;
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
			className="scroll-mt-24 outline-none [overflow-wrap:anywhere]"
			data-activity-id={item.id}
			data-activity-kind={item.kind}
			data-highlighted={highlighted ? "true" : "false"}
		>
			<div
				className={cn(
					"grid min-w-0 grid-cols-[auto_auto_1fr] gap-2 px-3 py-2.5 md:grid-cols-[minmax(0,1fr)_5rem_6rem_4rem] md:gap-3",
					selected && "bg-[var(--bf-info-soft)]/55",
					highlighted && "ring-2 ring-inset ring-[var(--bf-info)]/45",
				)}
			>
				<div
					className="col-span-3 flex min-w-0 items-start gap-2 md:col-span-1"
					style={{ paddingLeft: `${rowDepth * 1.5}rem` }}
				>
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
							"mt-1 grid size-7 shrink-0 place-items-center rounded-[var(--bf-radius-control)] text-muted-foreground",
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
							<Icon className="size-4" />
						</span>
						<span className="min-w-0">
							<span className="block break-words text-sm font-medium leading-5">
								{title}
							</span>
							{caption ? (
								<span className="mt-0.5 line-clamp-2 break-words text-xs leading-5 text-muted-foreground">
									{caption}
								</span>
							) : null}
						</span>
					</button>
				</div>
				<div className="flex items-start pt-1 pl-11 text-xs text-muted-foreground md:pl-0">
					{rowType}
				</div>
				<div className="flex items-start pt-1">
					{status ? (
						<DelegationStatusBadge id={statusId} status={status} />
					) : (
						<span className="text-xs text-muted-foreground">
							{runStatus === "running"
								? "In progress"
								: "No status"}
						</span>
					)}
				</div>
				<div className="flex items-start pt-1 text-xs tabular-nums text-muted-foreground">
					{item.durationMs != null
						? formatDuration(item.durationMs)
						: "—"}
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
				<ol className="divide-y divide-border/70 border-t border-border/70">
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
	item,
	childRunOrigin,
	onOpenChildRun,
}: {
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
	const title = child?.agent_name ?? item.agentName ?? item.title;
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
	const outputDetail = activityOutputDetail(item, child);
	const usage = child?.ai_usage ?? [];
	const hasUsage = usage.length > 0 || !!child?.ai_totals;
	const overviewOutcome = child?.did ?? child?.answered ?? item.description;
	const tabs = [
		["overview", "Overview", true],
		["input", "Input", !!inputDetail],
		["output", "Output", !!outputDetail || !!child],
		["usage", "Usage", hasUsage],
	] as const;

	return (
		<section
			className="min-w-0 rounded-[var(--bf-radius-feature)] border border-border/70 bg-background/65 p-4"
			aria-label="Selected call details"
		>
			<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div className="min-w-0">
					<p className="text-xs text-muted-foreground">
						Selected call
					</p>
					<h3 className="mt-1 break-words text-lg font-semibold leading-7">
						{title}
					</h3>
					{item.task || item.description ? (
						<p className="mt-1 break-words text-sm leading-6 text-muted-foreground">
							{item.task ?? item.description}
						</p>
					) : null}
				</div>
				<div className="flex shrink-0 flex-wrap items-center gap-2">
					{item.executionId ? (
						<Link
							to={`/history/${item.executionId}`}
							onClick={() => onOpenChildRun?.(item.id)}
							className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-3 text-sm font-medium text-primary hover:bg-[var(--bf-info-soft)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
							className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-3 text-sm font-medium text-primary hover:bg-[var(--bf-info-soft)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							Open run
							<ArrowUpRight className="size-4" />
						</Link>
					) : null}
				</div>
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
				defaultValue="overview"
				className="mt-4 min-w-0 gap-4"
			>
				<TabsList
					variant="line"
					className="flex min-h-11 max-w-full justify-start overflow-x-auto"
					aria-label="Selected call detail sections"
				>
					{tabs.map(([value, label, enabled]) => (
						<TabsTrigger
							key={value}
							value={value}
							disabled={!enabled}
							className="min-h-11 shrink-0 px-2 sm:px-3"
						>
							{label}
						</TabsTrigger>
					))}
				</TabsList>
				<TabsContent value="overview" className="mt-0 min-w-0">
					<div className="grid gap-5">
						<OverviewBlock label="Task">
							{child?.asked ??
								item.task ??
								"No task summary recorded."}
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
					{inputDetail ? <DetailBlock detail={inputDetail} /> : null}
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
			<div className="max-h-[320px] overflow-y-auto rounded-[var(--bf-radius-feature)] border border-border/70 bg-muted/60 p-2.5">
				<VariablesTreeView data={asVariableRecord(detail.value)} />
			</div>
		);
	}
	const parsed = tryParseJson(detail.value);
	if (parsed !== UNPARSEABLE) {
		return (
			<div className="max-h-[320px] overflow-y-auto rounded-[var(--bf-radius-feature)] border border-border/70 bg-muted/60 p-2.5">
				<VariablesTreeView data={asVariableRecord(parsed)} />
			</div>
		);
	}
	return (
		<div className="max-h-[320px] overflow-y-auto rounded-[var(--bf-radius-feature)] border border-border/70 bg-muted/60 px-3 py-2 text-sm leading-6 whitespace-pre-wrap break-words">
			{detail.value}
		</div>
	);
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
