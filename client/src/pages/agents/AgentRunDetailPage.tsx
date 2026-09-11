import {
	PageWorkspace,
	PageScrollArea,
} from "@/components/layout/PageWorkspace";
import { RunAIUsageCard } from "./RunAIUsageCard";
import { SummaryRegenerationControl } from "@/components/agents/SummaryRegenerationControl";
/**
 * AgentRunDetailPage — full-page detail view for a single agent run.
 *
 * Routes:
 *   /agents/:agentId/runs/:runId  → this page
 *
 * Layout:
 *   - Page header (contextual back link + run summary + status badge)
 *   - Main column: <RunReviewPanel variant="page"> + grouped Activity with
 *     an explicit Advanced mode for raw executor records and payloads
 *   - Sidebar: run metadata, AI usage cost breakdown, regen-summary button
 *     (admins only; failed-summary recovery lives in the review panel), and per-flag conversation when the
 *     run's verdict is "down"
 *
 * Replaces (T33) the legacy `client/src/pages/AgentRunDetail.tsx`.
 *
 * Ported from /tmp/agent-mockup/src/pages/RunDetailPage.tsx — uses real
 * hooks, shadcn primitives, Tailwind. No inline styles.
 */

import { useAgentRunStepStore } from "@/stores/agentRunStepStore";
import { RunActivityHeader } from "./RunActivityHeader";
import { RunActionFeedback } from "./RunActionFeedback";
import { FleetReadError } from "./FleetReadError";
import {
	useMemo,
	useRef,
	useState,
	type MouseEvent as ReactMouseEvent,
} from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
	AlertCircle,
	ArrowLeft,
	Bot,
	CheckCircle,
	ChevronRight,
	Code2,
	Clock,
	Loader2,
	RefreshCw,
	Sparkles,
	XCircle,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { RunDetailHeading } from "@/components/execution/RunDetailHeading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts/AuthContext";
import { useAgent } from "@/hooks/useAgents";
import { useAgentRunUpdates } from "@/hooks/useAgentRunUpdates";
import {
	createAgentRunNavigationState,
	getLocationHref,
	readAgentRunNavigationOrigin,
	type AgentRunNavigationOrigin,
} from "@/lib/agent-run-navigation";
import { formatDuration, formatNumber } from "@/lib/utils";
import {
	useAgentRun,
	useAgentRunStream,
	useClearVerdict,
	useFlagConversation,
	useRerunAgentRun,
	useSendFlagMessage,
	useSetVerdict,
} from "@/services/agentRuns";
import type { components } from "@/lib/v1";

import { FlagConversation } from "@/components/agents/FlagConversation";
import {
	RunReviewPanel,
	RunPayloads,
	type Verdict,
} from "@/components/agents/RunReviewPanel";
import { AdvancedTimeline, Timeline } from "@/components/agents/Timeline";
import { activityDomId } from "@/components/agents/run-activity";

type AgentRunDetailResponse = components["schemas"]["AgentRunDetailResponse"];

export function AgentRunDetailPage() {
	const { agentId, runId } = useParams<{
		agentId: string;
		runId: string;
	}>();
	const queryClient = useQueryClient();
	const { isPlatformAdmin } = useAuth();
	const location = useLocation();
	const navigate = useNavigate();
	const navigationOrigin = readAgentRunNavigationOrigin(location.state);

	// `useAgentRun` returns a hand-rolled `AgentRunDetail` type that predates
	// some OpenAPI fields (asked/did/verdict/etc). Re-cast to the OpenAPI
	// schema for full field access.
	const {
		data: rawRun,
		isLoading,
		isError: runError,
		isFetching: runFetching,
		refetch: refetchRun,
	} = useAgentRun(runId);
	useAgentRunStream(runId);
	const streamedSteps = useAgentRunStepStore((state) =>
		runId ? state.streams[runId]?.steps : undefined,
	);
	const run = useMemo(() => {
		const fetched = rawRun as unknown as AgentRunDetailResponse | undefined;
		if (!fetched || !streamedSteps?.length) return fetched;
		const steps = new Map(
			[...streamedSteps, ...(fetched.steps ?? [])].map((step) => [
				step.id,
				step,
			]),
		);
		return {
			...fetched,
			steps: [...steps.values()].sort(
				(a, b) => a.step_number - b.step_number,
			),
		} as AgentRunDetailResponse;
	}, [rawRun, streamedSteps]);
	const owningAgentId = run?.agent_id ?? agentId;
	const {
		data: agent,
		isError: agentError,
		isFetching: agentFetching,
		refetch: refetchAgent,
	} = useAgent(owningAgentId);
	const parentRunId = navigationOrigin
		? undefined
		: (run?.parent_run_id ?? undefined);
	const {
		data: rawParentRun,
		isError: parentError,
		isFetching: parentFetching,
		refetch: refetchParent,
	} = useAgentRun(parentRunId);
	const parentRun = parentRunId
		? (rawParentRun as unknown as AgentRunDetailResponse | undefined)
		: undefined;

	// Refetch this run whenever the backend broadcasts an update for it —
	// covers summarizer transitions (pending → generating → completed) and
	// step-writes so the page reflects live state without a manual refresh.
	useAgentRunUpdates({ agentId: owningAgentId });

	const verdict = ((run?.verdict as Verdict | undefined) ?? null) as Verdict;
	const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
	const note = runId ? (noteDrafts[runId] ?? run?.verdict_note ?? "") : "";
	const setNote = (value: string) => {
		if (runId)
			setNoteDrafts((previous) => ({ ...previous, [runId]: value }));
	};
	const verdictBusy = useRef(false);
	const [savingVerdict, setSavingVerdict] = useState(false);
	const [verdictFailure, setVerdictFailure] = useState<{
		runId: string;
		verdict: Verdict;
	} | null>(null);
	const [advancedView, setAdvancedView] = useState(false);
	const [previewedActivityId, setPreviewedActivityId] = useState<
		string | null
	>(null);
	const [expandedDelegationsByRun, setExpandedDelegationsByRun] = useState<
		ReadonlyMap<string, ReadonlySet<string>>
	>(() => {
		const saved = location.state?.runActivity;
		return saved?.runId === runId && Array.isArray(saved.expanded)
			? new Map([
					[
						runId!,
						new Set<string>(
							saved.expanded.filter(
								(id: unknown): id is string =>
									typeof id === "string",
							),
						),
					],
				])
			: new Map();
	});
	const [restoreActivityByRun, setRestoreActivityByRun] = useState<
		ReadonlyMap<string, string>
	>(() => {
		const saved = location.state?.runActivity;
		return saved?.runId === runId && typeof saved.restore === "string"
			? new Map([[runId!, saved.restore]])
			: new Map();
	});

	const setVerdict = useSetVerdict();
	const clearVerdict = useClearVerdict();
	const rerun = useRerunAgentRun();
	const rerunBusy = useRef(false);
	const [rerunFailure, setRerunFailure] = useState<string | null>(null);
	const currentRunOrigin: AgentRunNavigationOrigin | null = run
		? {
				href: getLocationHref(location),
				label: `Back to ${run.agent_name ?? agent?.name ?? "parent"} run`,
			}
		: null;

	const isFlagged = verdict === "down";
	const {
		data: conversation,
		isLoading: conversationLoading,
		isError: conversationError,
		isFetching: conversationFetching,
		refetch: refetchConversation,
	} = useFlagConversation(isFlagged ? runId : undefined);
	const sendMessage = useSendFlagMessage();

	function invalidateRun() {
		queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
		queryClient.invalidateQueries({ queryKey: ["agent-runs", runId] });
	}

	function handleVerdict(next: Verdict) {
		if (!runId || verdictBusy.current) return;
		verdictBusy.current = true;
		setSavingVerdict(true);
		setVerdictFailure(null);
		const onSuccess = () => {
			setNoteDrafts((previous) => ({
				...previous,
				[runId]: next === null ? "" : note,
			}));
			invalidateRun();
			void queryClient.invalidateQueries({
				queryKey: ["agent-runs-infinite"],
			});
		};
		const onError = () => setVerdictFailure({ runId, verdict: next });
		const onSettled = () => {
			verdictBusy.current = false;
			setSavingVerdict(false);
		};
		if (next === null)
			clearVerdict.mutate(
				{ params: { path: { run_id: runId } } },
				{ onSuccess, onError, onSettled },
			);
		else
			setVerdict.mutate(
				{
					params: { path: { run_id: runId } },
					body: { verdict: next, note },
				},
				{ onSuccess, onError, onSettled },
			);
	}

	function handleSendChat(text: string): Promise<void> {
		return new Promise((resolve, reject) => {
			if (!runId) {
				reject(new Error("Run unavailable"));
				return;
			}
			sendMessage.mutate(
				{
					params: { path: { run_id: runId } },
					body: { content: text },
				},
				{
					onSuccess: (data) => {
						queryClient.setQueryData(
							[
								"get",
								"/api/agent-runs/{run_id}/flag-conversation",
								{ params: { path: { run_id: runId } } },
							],
							data,
						);
						resolve();
					},
					onError: reject,
				},
			);
		});
	}

	function handleRerun() {
		if (!runId || !run?.agent_id || rerunBusy.current) return;
		rerunBusy.current = true;
		setRerunFailure(null);
		rerun.mutate(
			{ params: { path: { run_id: runId } } },
			{
				onSuccess: (data) => {
					toast.success("Rerun queued");
					if (data.run_id && currentRunOrigin) {
						navigate(
							`/agents/${run.agent_id}/runs/${data.run_id}`,
							{
								state: createAgentRunNavigationState(
									currentRunOrigin,
								),
							},
						);
					}
				},
				onError: () => setRerunFailure(runId),
				onSettled: () => {
					rerunBusy.current = false;
				},
			},
		);
	}

	function handleContextBackClick(event: ReactMouseEvent<HTMLAnchorElement>) {
		if (
			!navigationOrigin ||
			event.defaultPrevented ||
			event.button !== 0 ||
			event.metaKey ||
			event.ctrlKey ||
			event.shiftKey ||
			event.altKey
		) {
			return;
		}

		event.preventDefault();
		navigate(-1);
	}

	function handleActivityReferenceActivate(activityId: string) {
		const target = document.getElementById(activityDomId(activityId));
		if (!target) return;
		const reduceMotion =
			window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ??
			false;
		target.scrollIntoView({
			behavior: reduceMotion ? "auto" : "smooth",
			block: "center",
		});
		target.focus({ preventScroll: true });
	}

	function handleDelegationExpandedChange(
		activityId: string,
		expanded: boolean,
	) {
		if (!runId) return;
		setExpandedDelegationsByRun((current) => {
			const nextForRun = new Set(current.get(runId) ?? []);
			if (expanded) {
				nextForRun.add(activityId);
			} else {
				nextForRun.delete(activityId);
			}
			const next = new Map(current);
			next.set(runId, nextForRun);
			return next;
		});
	}

	function handleOpenChildRun(activityId: string) {
		if (!runId) return;
		navigate(getLocationHref(location), {
			replace: true,
			state: {
				...location.state,
				runActivity: {
					runId,
					expanded: [...(expandedDelegationsByRun.get(runId) ?? [])],
					restore: activityId,
				},
			},
		});
		setPreviewedActivityId(null);
		setRestoreActivityByRun((current) => {
			const next = new Map(current);
			next.set(runId, activityId);
			return next;
		});
	}

	if (isLoading) {
		return (
			<div className="flex flex-col gap-5 max-w-7xl mx-auto">
				<Skeleton className="h-6 w-32" />
				<Skeleton className="h-12 w-1/2" />
				<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<div className="lg:col-span-2 space-y-4">
						<Skeleton className="h-64 w-full" />
					</div>
					<div className="space-y-4">
						<Skeleton className="h-48 w-full" />
					</div>
				</div>
			</div>
		);
	}

	if (runError && !run) {
		return (
			<div className="mx-auto flex max-w-7xl flex-col gap-4">
				<Button asChild variant="outline" className="w-fit min-h-11">
					<Link
						to={
							navigationOrigin?.href ??
							(agentId ? `/agents/${agentId}` : "/agents")
						}
						onClick={handleContextBackClick}
					>
						{navigationOrigin?.label ?? "Back to agent"}
					</Link>
				</Button>
				<h1 className="font-display text-2xl font-semibold">
					Agent run
				</h1>
				<FleetReadError
					resource="run details"
					cached={false}
					pending={runFetching}
					onRetry={() => void refetchRun()}
				/>
			</div>
		);
	}

	if (!run) {
		const notFoundBackHref =
			navigationOrigin?.href ??
			(agentId ? `/agents/${agentId}` : "/agents");
		return (
			<div
				className="flex flex-col items-center justify-center gap-3 py-16 text-center"
				data-testid="run-not-found"
			>
				<AlertCircle className="h-10 w-10 text-muted-foreground" />
				<div className="text-lg font-medium">Run not found</div>
				<Button asChild variant="outline">
					<Link
						to={notFoundBackHref}
						onClick={handleContextBackClick}
					>
						{navigationOrigin?.label ?? "Back to agent"}
					</Link>
				</Button>
			</div>
		);
	}

	const summaryStatus =
		(run as unknown as { summary_status?: string }).summary_status ?? null;
	const summaryFailed = summaryStatus === "failed";
	const summaryInFlight =
		summaryStatus === "pending" || summaryStatus === "generating";
	// While the summarizer is running, the RunReviewPanel already shows a
	// status banner with a regenerate button — hide the sidebar card so we
	// don't render two competing affordances.
	const showRegen = isPlatformAdmin && !summaryFailed && !summaryInFlight;
	// Header title: `asked` is the user-facing TL;DR (capped ~100 chars by
	// the summarizer prompt). `did` is a multi-sentence narrative under v3+
	// and too long for a title; only fall back to it when `asked` is empty.
	const headerSummary = run.agent_name || agent?.name || "Agent run";
	const parentRunHref = parentRun?.agent_id
		? `/agents/${parentRun.agent_id}/runs/${parentRun.id}`
		: null;
	const backHref =
		navigationOrigin?.href ??
		parentRunHref ??
		(run.agent_id ? `/agents/${run.agent_id}` : "/agents");
	const backLabel =
		navigationOrigin?.label ??
		(parentRunHref
			? `Back to ${parentRun?.agent_name ?? "parent"} run`
			: run.agent_id
				? `Back to ${agent?.name ?? run.agent_name ?? "agent"}`
				: "Back to agents");

	return (
		<PageWorkspace
			className="flex flex-col gap-5 max-w-7xl mx-auto"
			data-testid="agent-run-detail-page"
		>
			<div className="shrink-0 space-y-6">
				{runError ? (
					<FleetReadError
						resource="run details"
						cached
						pending={runFetching}
						onRetry={() => void refetchRun()}
					/>
				) : null}
				{agentError ? (
					<FleetReadError
						resource="agent information"
						cached={!!agent}
						pending={agentFetching}
						onRetry={() => void refetchAgent()}
					/>
				) : null}
				{parentRunId && parentError ? (
					<FleetReadError
						resource="parent run"
						cached={!!parentRun}
						pending={parentFetching}
						onRetry={() => void refetchParent()}
					/>
				) : null}
				{/* Breadcrumb */}
				<Link
					to={backHref}
					onClick={handleContextBackClick}
					data-testid="run-context-back"
					className="inline-flex min-h-11 max-w-full w-fit items-center gap-2 rounded-[var(--bf-radius-control)] text-sm text-muted-foreground [overflow-wrap:anywhere] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				>
					<ArrowLeft aria-hidden="true" className="size-4 shrink-0" />
					{backLabel}
				</Link>

				<RunDetailHeading
					title={headerSummary}
					metadata={
						<div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
							<RunStatusBadge status={run.status} />
							{run.started_at ? (
								<span className="inline-flex items-center gap-1">
									<Clock className="h-3 w-3" />
									{new Date(run.started_at).toLocaleString()}
								</span>
							) : null}
							{run.duration_ms != null ? (
								<>
									<span>·</span>
									<span>
										{formatDuration(run.duration_ms)}
									</span>
								</>
							) : null}
						</div>
					}
					actionsLabel="Agent run actions"
					actions={
						<Button
							type="button"
							variant="outline"
							className="min-h-11 min-w-0"
							data-testid="rerun-button"
							disabled={rerun.isPending || !run.agent_id}
							onClick={handleRerun}
						>
							{rerun.isPending ? (
								<Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
							) : (
								<RefreshCw className="h-3.5 w-3.5" />
							)}
							Rerun
						</Button>
					}
				/>

				<RunActionFeedback
					pending={rerun.isPending}
					failed={rerunFailure === runId}
					onRetry={handleRerun}
					message="Could not queue a new run. Try again to rerun this execution."
					pendingLabel="Queuing rerun…"
					retryLabel="Retry rerun"
				/>
			</div>

			<PageScrollArea className="space-y-6">
				<div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
					<div className="lg:col-span-2 flex min-w-0 flex-col gap-4">
						<RunActionFeedback
							pending={savingVerdict}
							failed={verdictFailure?.runId === runId}
							onRetry={() => {
								if (verdictFailure)
									handleVerdict(verdictFailure.verdict);
							}}
						/>
						<fieldset
							disabled={savingVerdict}
							className="min-w-0"
							aria-label="Run review"
						>
							<Card className="min-w-0 overflow-hidden">
								<RunReviewPanel
									run={run}
									variant="page"
									verdict={verdict}
									note={note}
									onVerdict={handleVerdict}
									onNote={setNote}
									onActivityReferencePreview={
										setPreviewedActivityId
									}
									onActivityReferenceActivate={
										handleActivityReferenceActivate
									}
								/>
							</Card>
							{verdict && note !== (run.verdict_note ?? "") ? (
								<Button
									className="mt-3"
									onClick={() => handleVerdict(verdict)}
								>
									Save review note
								</Button>
							) : null}
						</fieldset>

						<section data-slot="run-activity" className="min-w-0">
							<RunActivityHeader
								className="px-0"
								advanced={advancedView}
								onChange={setAdvancedView}
							/>
							<div className="min-w-0 pt-4">
								<div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5 [&>*]:min-w-0">
									<Timeline
										steps={run.steps ?? []}
										childRunIds={run.child_run_ids ?? []}
										childRuns={run.child_runs ?? []}
										runStatus={run.status}
										showTechnicalDetails={advancedView}
										highlightedActivityId={
											previewedActivityId
										}
										expandedDelegationIds={
											runId
												? expandedDelegationsByRun.get(
														runId,
													)
												: undefined
										}
										onDelegationExpandedChange={
											handleDelegationExpandedChange
										}
										restoreActivityId={
											runId
												? restoreActivityByRun.get(
														runId,
													)
												: null
										}
										onOpenChildRun={handleOpenChildRun}
										childRunOrigin={
											currentRunOrigin ?? undefined
										}
									/>
									{advancedView &&
									(run.input || run.output) ? (
										<section className="border-t pt-4">
											<div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
												Run payloads
											</div>
											<RunPayloads
												input={run.input}
												output={run.output}
											/>
										</section>
									) : null}
									{advancedView &&
									(run.steps?.length ?? 0) > 0 ? (
										<details
											className="group min-w-0 border-t pt-4"
											data-slot="raw-executor-trace"
										>
											<summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-md px-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
												<ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90 motion-reduce:transition-none" />
												<Code2 className="h-3.5 w-3.5" />
												<span>Raw executor trace</span>
												<span className="ml-auto font-normal tabular-nums">
													{run.steps?.length ?? 0}{" "}
													events
												</span>
											</summary>
											<div className="mt-2.5 min-w-0 overflow-x-auto rounded-[var(--bf-radius-control)] border bg-background/50 p-3">
												<AdvancedTimeline
													steps={run.steps ?? []}
												/>
											</div>
										</details>
									) : null}
								</div>
							</div>
						</section>

						{/* Per-flag conversation (only when verdict=down) */}
						{isFlagged ? (
							<Card data-testid="flag-conversation-card">
								<CardHeader className="pb-2">
									<CardTitle className="flex items-center gap-2 text-sm">
										<Sparkles className="h-4 w-4" />
										Tuning conversation
									</CardTitle>
								</CardHeader>
								<CardContent className="p-0">
									{conversationError ? (
										<div className="px-4 pb-3">
											<FleetReadError
												resource="tuning conversation"
												cached={!!conversation}
												pending={conversationFetching}
												onRetry={() =>
													void refetchConversation()
												}
											/>
										</div>
									) : null}
									{conversationLoading ? (
										<div className="p-4">
											<Skeleton className="h-40 w-full" />
										</div>
									) : conversationError &&
									  !conversation ? null : (
										<div className="flex h-[420px] flex-col">
											<FlagConversation
												conversation={
													conversation ?? null
												}
												onSend={handleSendChat}
												pending={sendMessage.isPending}
											/>
										</div>
									)}
								</CardContent>
							</Card>
						) : null}
					</div>

					{/* Sidebar */}
					<div className="flex min-w-0 flex-col gap-4">
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-sm">
									Run details
								</CardTitle>
							</CardHeader>
							<CardContent>
								<details>
									<summary className="min-h-11 cursor-pointer text-sm text-muted-foreground">
										Metadata
									</summary>
									<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
										<MetaRow label="Run ID">
											<span className="font-mono text-[11px] break-all">
												{run.id}
											</span>
										</MetaRow>

										{run.started_at ? (
											<MetaRow label="Started">
												{new Date(
													run.started_at,
												).toLocaleString()}
											</MetaRow>
										) : null}
										<MetaRow label="Duration">
											{run.duration_ms != null
												? formatDuration(
														run.duration_ms,
													)
												: "—"}
										</MetaRow>

										<>
											<MetaRow label="Iterations">
												{run.iterations_used}
											</MetaRow>
											<MetaRow label="Tokens">
												{formatNumber(run.tokens_used)}
											</MetaRow>
											<MetaRow label="Model">
												<span className="font-mono">
													{run.llm_model ?? "default"}
												</span>
											</MetaRow>
										</>

										<MetaRow label="Trigger">
											{run.trigger_type}
										</MetaRow>
										{run.caller_email ? (
											<MetaRow label="Caller">
												{run.caller_name ??
													run.caller_email}
											</MetaRow>
										) : null}
									</dl>
								</details>
							</CardContent>
						</Card>

						{/* AI usage */}
						{run.ai_usage && run.ai_usage.length > 0 ? (
							<RunAIUsageCard
								usage={run.ai_usage}
								totals={run.ai_totals ?? null}
							/>
						) : null}

						{/* Admin regeneration for summaries without an active status banner. */}
						{showRegen ? (
							<Card>
								<CardContent className="flex flex-wrap items-center justify-between gap-3 py-3 text-xs">
									<div>
										<div className="font-medium">
											Summary
										</div>
										<div className="text-muted-foreground">
											Re-run the summarizer
										</div>
									</div>
									<SummaryRegenerationControl
										runId={run.id}
										allowed={isPlatformAdmin}
										testId="regen-summary-button"
									/>
								</CardContent>
							</Card>
						) : null}

						{/* Agent card */}
						<Card>
							<CardHeader className="pb-2">
								<CardTitle className="text-sm">Agent</CardTitle>
							</CardHeader>
							<CardContent>
								{run.agent_id ? (
									<Link
										to={`/agents/${run.agent_id}`}
										className="flex items-start gap-2 text-sm hover:underline"
									>
										<Bot className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
										<div className="min-w-0">
											<div className="truncate font-medium">
												{agent?.name ??
													run.agent_name ??
													"Agent"}
											</div>
											{agent?.description ? (
												<div className="text-xs text-muted-foreground line-clamp-2">
													{agent.description}
												</div>
											) : null}
										</div>
									</Link>
								) : (
									<div className="space-y-1 text-sm">
										<p className="font-medium [overflow-wrap:anywhere]">
											{run.agent_name ?? "Deleted agent"}
										</p>
										<p className="text-xs text-muted-foreground">
											This agent is no longer available.
										</p>
									</div>
								)}
							</CardContent>
						</Card>
					</div>
				</div>
			</PageScrollArea>
		</PageWorkspace>
	);
}

function MetaRow({
	label,
	children,
}: {
	label: string;
	children: React.ReactNode;
}) {
	return (
		<>
			<dt className="text-muted-foreground">{label}</dt>
			<dd className="min-w-0 text-right text-foreground [overflow-wrap:anywhere]">
				{children}
			</dd>
		</>
	);
}

function RunStatusBadge({ status }: { status: string }) {
	switch (status) {
		case "completed":
			return (
				<Badge
					variant="outline"
					className="border-[color:var(--bf-success)]/30 bg-[color:var(--bf-success)]/10 text-[color:var(--bf-success)]"
				>
					<CheckCircle className="h-3 w-3" /> Completed
				</Badge>
			);
		case "failed":
			return (
				<Badge
					variant="outline"
					className="border-[color:var(--bf-danger)]/30 bg-[color:var(--bf-danger)]/10 text-[color:var(--bf-danger)]"
				>
					<XCircle className="h-3 w-3" /> Failed
				</Badge>
			);
		case "running":
			return (
				<Badge
					variant="outline"
					className="border-primary/30 bg-primary/10 text-primary"
				>
					<Loader2 className="h-3 w-3 animate-spin motion-reduce:animate-none" />{" "}
					Running
				</Badge>
			);
		case "budget_exceeded":
			return (
				<Badge
					variant="outline"
					className="border-[color:var(--bf-warning)]/30 bg-[color:var(--bf-warning)]/10 text-[color:var(--bf-warning)]"
				>
					<AlertCircle className="h-3 w-3" /> Budget exceeded
				</Badge>
			);
		default:
			return <Badge variant="outline">{status}</Badge>;
	}
}
