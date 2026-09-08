import { Button } from "@/components/ui/button";
/**
 * Timeline has two deliberately different projections of a run:
 *
 * - Timeline: a user-facing activity story. It groups the executor's
 *   decision/call/result records into one operation and nests child runs.
 * - AdvancedTimeline: the exact step sequence with raw payload disclosure.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
	AlertCircle,
	ArrowUpRight,
	Bot,
	Check,
	ChevronRight,
	CircleDot,
	Code2,
	Cpu,
	GitBranch,
	Loader2,
	MessageSquare,
	MessageSquareText,
	TriangleAlert,
	Wrench,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { formatDuration, formatNumber } from "@/lib/utils";
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

const ACTIVE_RUN_STATUSES = new Set(["queued", "running", "cancelling"]);

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
	childRunIds = [],
	childRuns = [],
	runStatus,
	showTechnicalDetails = false,
	highlightedActivityId = null,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId = null,
	onOpenChildRun,
	childRunOrigin,
	depth = 0,
}: TimelineProps) {
	const activity = buildRunActivity(steps, childRunIds, childRuns);
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

	return (
		<ol
			className="relative grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 before:absolute before:bottom-5 before:left-[11px] sm:before:left-[21px] before:top-5 before:w-px before:bg-border"
			aria-label="Run activity"
		>
			{activity.map((item) => (
				<ActivityRow
					key={item.id}
					item={item}
					depth={depth}
					runStatus={runStatus}
					showTechnicalDetails={showTechnicalDetails}
					highlighted={item.id === highlightedActivityId}
					expandedDelegationIds={expandedDelegationIds}
					onDelegationExpandedChange={onDelegationExpandedChange}
					restoreActivityId={restoreActivityId}
					onOpenChildRun={onOpenChildRun}
					childRunOrigin={childRunOrigin}
				/>
			))}
		</ol>
	);
}

function ActivityRow({
	item,
	depth,
	runStatus,
	showTechnicalDetails,
	highlighted,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId,
	onOpenChildRun,
	childRunOrigin,
}: {
	item: RunActivityItem;
	depth: number;
	runStatus?: string | null;
	showTechnicalDetails: boolean;
	highlighted: boolean;
	expandedDelegationIds?: ReadonlySet<string>;
	onDelegationExpandedChange?: (
		activityId: string,
		expanded: boolean,
	) => void;
	restoreActivityId?: string | null;
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
}) {
	if (item.kind === "delegation") {
		return (
			<DelegationRow
				item={item}
				depth={depth}
				showTechnicalDetails={showTechnicalDetails}
				highlighted={highlighted}
				expandedDelegationIds={expandedDelegationIds}
				onDelegationExpandedChange={onDelegationExpandedChange}
				restoreActivityId={restoreActivityId}
				onOpenChildRun={onOpenChildRun}
				childRunOrigin={childRunOrigin}
			/>
		);
	}

	const isError = item.isError || item.kind === "error";
	const isWarning = item.kind === "warning";
	const isCancelled = item.kind === "cancelled";
	const isResponse = item.kind === "response";
	const pending = item.kind === "action" && !item.resultStep;
	const runInProgress = ["queued", "running", "cancelling"].includes(
		runStatus ?? "",
	);
	const Icon = isError
		? AlertCircle
		: isWarning || isCancelled
			? TriangleAlert
			: isResponse
				? MessageSquareText
				: pending
					? CircleDot
					: Check;
	const tone = isError
		? "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60"
		: isWarning || isCancelled
			? "border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)]/60"
			: "border-border/70 bg-card";
	const iconTone = isError
		? "border-[var(--bf-danger)]/25 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
		: isWarning || isCancelled
			? "border-[var(--bf-warning)]/25 bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]"
			: isResponse
				? "border-[var(--bf-info)]/25 bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
				: pending
					? runInProgress
						? "border-[var(--bf-info)]/25 bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
						: "border-border bg-muted text-muted-foreground"
					: "border-[var(--bf-success)]/25 bg-[var(--bf-success-soft)] text-[var(--bf-success)]";

	return (
		<li
			id={activityDomId(item.id)}
			tabIndex={-1}
			className="relative scroll-mt-24 rounded-[var(--bf-radius-feature)] pl-8 outline-none [overflow-wrap:anywhere] sm:pl-12"
			data-activity-id={item.id}
			data-activity-kind={item.kind}
			data-highlighted={highlighted ? "true" : "false"}
		>
			<div
				className={cn(
					"absolute left-0 top-3 z-10 grid size-6 place-items-center sm:size-11 rounded-full border shadow-sm",
					iconTone,
				)}
			>
				<Icon className="h-4 w-4" />
			</div>
			<div
				className={cn(
					"rounded-[var(--bf-radius-feature)] border px-4 py-4 shadow-sm transition-[border-color,background-color,box-shadow] duration-150 motion-reduce:transition-none",
					tone,
					highlighted &&
						"border-[var(--bf-info)]/50 ring-2 ring-[var(--bf-info)]/45 ring-offset-2 ring-offset-background",
				)}
			>
				<div className="flex items-start gap-3">
					<div className="min-w-0 flex-1">
						<div className="text-sm font-medium leading-5">
							{item.title}
						</div>
						{item.description ? (
							<p className="mt-1 text-sm leading-6 text-muted-foreground">
								{item.description}
							</p>
						) : pending ? (
							<p className="mt-1 text-sm leading-6 text-muted-foreground">
								{runInProgress
									? "In progress"
									: "No outcome recorded"}
							</p>
						) : null}
					</div>
					<div className="flex shrink-0 items-center gap-2 pt-0.5">
						{item.durationMs != null ? (
							<span className="text-[11px] tabular-nums text-muted-foreground">
								{formatDuration(item.durationMs)}
							</span>
						) : null}
						{item.executionId ? (
							<Link
								to={`/history/${item.executionId}`}
								className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-2 text-sm font-medium text-primary transition-colors hover:bg-[var(--bf-info-soft)]/80 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
							>
								Execution
								<ArrowUpRight className="h-4 w-4" />
							</Link>
						) : null}
					</div>
				</div>
				{showTechnicalDetails ? (
					<ActivityTechnicalDetails item={item} />
				) : null}
			</div>
		</li>
	);
}

function ActivityTechnicalDetails({ item }: { item: RunActivityItem }) {
	const callContent = (item.callStep?.content ?? {}) as Record<
		string,
		unknown
	>;
	const resultContent = (item.resultStep?.content ?? {}) as Record<
		string,
		unknown
	>;
	const inputDetail = renderDetail(callContent.arguments);
	const resultValue =
		item.resultStep?.type === "llm_response"
			? resultContent.content
			: item.isError
				? (resultContent.error ?? resultContent.result ?? resultContent)
				: (resultContent.result ??
					(item.resultStep && !item.toolName ? resultContent : null));
	const resultDetail = renderDetail(resultValue);
	const stepNumbers = [
		item.callStep?.step_number,
		item.resultStep?.step_number,
	].filter((value): value is number => value != null);
	const tokens = [item.callStep, item.resultStep].reduce(
		(total, step) => total + (step?.tokens_used ?? 0),
		0,
	);
	const hasMetadata = !!item.toolName || stepNumbers.length > 0 || tokens > 0;

	if (!hasMetadata && !inputDetail && !resultDetail) return null;

	return (
		<details className="group mt-3 border-t border-border/70 pt-2.5">
			<summary className="flex min-h-11 cursor-pointer list-none items-center gap-1.5 rounded-[var(--bf-radius-control)] px-2 text-sm font-medium text-muted-foreground transition-colors motion-reduce:transition-none hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background [&::-webkit-details-marker]:hidden">
				<ChevronRight className="h-4 w-4 transition-transform motion-reduce:transition-none group-open:rotate-90" />
				<Code2 className="h-4 w-4" />
				Details
			</summary>
			<div className="mt-2.5 grid gap-3 rounded-[var(--bf-radius-feature)] border border-border/70 bg-background/65 p-3">
				{hasMetadata ? (
					<dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
						{item.toolName ? (
							<>
								<dt className="text-muted-foreground">
									Internal action
								</dt>
								<dd className="min-w-0 break-all font-mono text-[13px] leading-6">
									{item.toolName}
								</dd>
							</>
						) : null}
						{stepNumbers.length ? (
							<>
								<dt className="text-muted-foreground">Trace</dt>
								<dd>
									{stepNumbers.length === 1 ||
									stepNumbers[0] === stepNumbers.at(-1)
										? `Step ${stepNumbers[0]}`
										: `Steps ${stepNumbers[0]}–${stepNumbers.at(-1)}`}
								</dd>
							</>
						) : null}
						{tokens > 0 ? (
							<>
								<dt className="text-muted-foreground">
									Tokens
								</dt>
								<dd>{formatNumber(tokens)}</dd>
							</>
						) : null}
					</dl>
				) : null}
				{inputDetail ? (
					<TechnicalDetailSection
						label="Input"
						detail={inputDetail}
					/>
				) : null}
				{resultDetail ? (
					<TechnicalDetailSection
						label={item.isError ? "Error" : "Result"}
						detail={resultDetail}
					/>
				) : null}
			</div>
		</details>
	);
}

function TechnicalDetailSection({
	label,
	detail,
}: {
	label: string;
	detail: DetailRender;
}) {
	return (
		<section>
			<div className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
				{label}
			</div>
			<DetailBlock detail={detail} />
		</section>
	);
}

function DelegationRow({
	item,
	depth,
	showTechnicalDetails,
	highlighted,
	expandedDelegationIds,
	onDelegationExpandedChange,
	restoreActivityId,
	onOpenChildRun,
	childRunOrigin,
}: {
	item: RunActivityItem;
	depth: number;
	showTechnicalDetails: boolean;
	highlighted: boolean;
	expandedDelegationIds?: ReadonlySet<string>;
	onDelegationExpandedChange?: (
		activityId: string,
		expanded: boolean,
	) => void;
	restoreActivityId?: string | null;
	onOpenChildRun?: (activityId: string) => void;
	childRunOrigin?: AgentRunNavigationOrigin;
}) {
	const [localOpen, setLocalOpen] = useState(false);
	const rowRef = useRef<HTMLLIElement>(null);
	const open =
		expandedDelegationIds !== undefined
			? expandedDelegationIds.has(item.id)
			: localOpen;

	useEffect(() => {
		if (restoreActivityId !== item.id) return;
		rowRef.current?.scrollIntoView({
			behavior: "auto",
			block: "center",
		});
	}, [item.id, restoreActivityId]);

	function toggleOpen() {
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
	const childAgentId = child?.agent_id ?? item.childAgentId;
	const title = agentName ?? "Delegated agent";
	const expandable = !!item.childRunId;
	const childStatus = child?.status ?? item.childStatus;
	const childFailed = childStatus ? isFailedRunStatus(childStatus) : false;
	const delegationFailed = item.isError || childFailed;
	const delegationStatus = childStatus ?? (item.isError ? "failed" : null);
	const delegationStatusId = delegationStatus
		? `${activityDomId(item.id)}-status`
		: undefined;
	const detailsId = `${activityDomId(item.id)}-details`;
	const childActivity = child
		? buildRunActivity(child.steps, child.child_run_ids, child.child_runs)
		: [];
	const childActivityReferences = buildActivityReferenceIndex(childActivity);
	const rowContent = (
		<>
			<div className="min-w-0 flex-1">
				<div className="flex flex-wrap items-center gap-x-2 gap-y-1">
					<span className="min-w-0 break-words text-sm font-medium leading-5">
						{title}
					</span>
					<span
						className={cn(
							"shrink-0 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-medium uppercase tracking-wide",
							delegationFailed
								? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
								: "bg-[var(--bf-info-soft)] text-[var(--bf-info)]",
						)}
					>
						Agent
					</span>
					{delegationStatus ? (
						<DelegationStatusBadge
							id={delegationStatusId}
							status={delegationStatus}
						/>
					) : null}
				</div>
				{item.task ? (
					<p className="mt-1 text-sm leading-6 text-muted-foreground">
						{item.task}
					</p>
				) : item.description ? (
					<p className="mt-1 text-sm leading-6 text-muted-foreground">
						{item.description}
					</p>
				) : null}
			</div>
			{!delegationStatus && item.durationMs != null ? (
				<div className="shrink-0 pt-0.5 text-sm text-muted-foreground">
					<span>{formatDuration(item.durationMs)}</span>
				</div>
			) : null}
		</>
	);

	return (
		<li
			ref={rowRef}
			id={activityDomId(item.id)}
			tabIndex={-1}
			className="relative scroll-mt-24 rounded-[var(--bf-radius-feature)] pl-8 outline-none [overflow-wrap:anywhere] sm:pl-12"
			data-activity-id={item.id}
			data-activity-kind="delegation"
			data-highlighted={highlighted ? "true" : "false"}
		>
			<div
				className={cn(
					"absolute left-0 top-3 z-10 grid size-6 place-items-center sm:size-11 rounded-full border shadow-sm",
					delegationFailed
						? "border-[var(--bf-danger)]/25 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
						: "border-[var(--bf-info)]/25 bg-[var(--bf-info-soft)] text-[var(--bf-info)]",
				)}
			>
				<GitBranch className="h-4 w-4" />
			</div>
			<div
				className={cn(
					"overflow-hidden rounded-[var(--bf-radius-feature)] border shadow-sm transition-[border-color,background-color,box-shadow] duration-150 motion-reduce:transition-none",
					delegationFailed
						? "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60"
						: "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)]/60",
					highlighted &&
						"border-[var(--bf-info)]/55 ring-2 ring-[var(--bf-info)]/45 ring-offset-2 ring-offset-background",
				)}
			>
				<div className="flex flex-col md:flex-row md:items-stretch">
					{expandable ? (
						<button
							type="button"
							onClick={toggleOpen}
							aria-expanded={open}
							aria-controls={detailsId}
							aria-label={`${open ? "Hide" : "Show"} details for ${title}`}
							aria-describedby={delegationStatusId}
							className={cn(
								"group flex min-h-11 min-w-0 flex-1 cursor-pointer items-start gap-3 px-4 py-4 text-left transition-colors motion-reduce:transition-none hover:bg-[var(--bf-info-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
								open && "bg-[var(--bf-info-soft)]/60",
							)}
						>
							{rowContent}
							{isLoading && open ? (
								<Loader2 className="h-4 w-4 shrink-0 self-center animate-spin text-[var(--bf-info)] motion-reduce:animate-none" />
							) : (
								<ChevronRight
									className={cn(
										"h-4 w-4 shrink-0 self-center text-muted-foreground transition-transform group-hover:text-foreground motion-reduce:transition-none",
										open && "rotate-90",
									)}
								/>
							)}
						</button>
					) : (
						<div className="flex min-w-0 flex-1 items-start gap-3 px-4 py-4 text-left">
							{rowContent}
						</div>
					)}
					{childAgentId && item.childRunId ? (
						<div className="flex shrink-0 items-center justify-end border-t border-[var(--bf-info)]/15 p-2 md:border-l md:border-t-0">
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
								aria-label={`Open ${title} run`}
								className="inline-flex min-h-11 items-center gap-1 rounded-[var(--bf-radius-control)] px-3 text-sm font-medium text-primary transition-colors hover:bg-[var(--bf-info-soft)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
							>
								<span>Open run</span>
								<ArrowUpRight className="h-4 w-4" />
							</Link>
						</div>
					) : null}
				</div>

				{open ? (
					<div
						id={detailsId}
						className="border-t border-[var(--bf-info)]/15 bg-background/45 px-4 py-4"
					>
						{isError ? (
							<div
								role="alert"
								className="mb-3 space-y-3 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-3 text-sm"
							>
								<p>
									Could not {child ? "refresh" : "load"}{" "}
									delegated run details.
									{child
										? " Previously loaded details are still shown."
										: ""}
								</p>
								<Button
									variant="outline"
									className="min-h-11"
									disabled={isFetching}
									onClick={() => void refetch()}
								>
									Retry delegated run
								</Button>
							</div>
						) : null}
						{isLoading ? (
							<div className="flex items-center gap-2 py-3 text-sm leading-6 text-muted-foreground">
								<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
								Loading delegated work…
							</div>
						) : !child ? (
							<p className="py-2 text-sm leading-6 text-muted-foreground">
								{isError
									? ""
									: "Delegated run details are not available."}
							</p>
						) : (
							<div className="grid gap-4">
								<div className="grid gap-2 sm:grid-cols-2">
									<DelegationSummary label="Task">
										{child.asked ??
											item.task ??
											"No task summary recorded."}
									</DelegationSummary>
									<DelegationSummary label="Outcome">
										<DidNarrative
											text={child.did ?? child.answered}
											activityReferences={
												childActivityReferences
											}
											compact
											fallback={
												<>
													No outcome summary recorded.
												</>
											}
										/>
									</DelegationSummary>
								</div>

								{depth < 3 &&
								((child.steps?.length ?? 0) > 0 ||
									(child.child_run_ids?.length ?? 0) > 0) ? (
									<div className="rounded-[var(--bf-radius-feature)] border border-border/70 bg-background/65 p-3">
										<div className="mb-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
											Activity
										</div>
										<Timeline
											steps={child.steps}
											childRunIds={child.child_run_ids}
											childRuns={child.child_runs}
											runStatus={child.status}
											showTechnicalDetails={
												showTechnicalDetails
											}
											expandedDelegationIds={
												expandedDelegationIds
											}
											onDelegationExpandedChange={
												onDelegationExpandedChange
											}
											restoreActivityId={
												restoreActivityId
											}
											onOpenChildRun={onOpenChildRun}
											childRunOrigin={childRunOrigin}
											depth={depth + 1}
										/>
									</div>
								) : null}
							</div>
						)}
					</div>
				) : null}
			</div>
		</li>
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

function DelegationSummary({
	label,
	children,
}: {
	label: string;
	children: ReactNode;
}) {
	return (
		<div className="rounded-xl border border-border/70 bg-background/70 px-3 py-3">
			<div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
				{label}
			</div>
			<div className="text-sm leading-6">{children}</div>
		</div>
	);
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
