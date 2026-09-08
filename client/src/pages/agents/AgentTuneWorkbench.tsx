/**
 * AgentTuneWorkbench — two-column tuning workbench.
 *
 * Left: flagged runs (expandable transcripts) + Generate proposal CTA.
 * Right: prompt editor (current collapsible, proposed editable with diff).
 *
 * Top-right header action: Run dry-run (enabled once a proposal exists).
 * Dry-run results, when present, render as a full-width panel below the
 * header.
 */

import { FleetReadError } from "./FleetReadError";
import { PageLoader } from "@/components/PageLoader";
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Loader2, PlayCircle, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { TuningActionError } from "./TuningActionError";
import { TuningDryRunResults } from "./TuningDryRunResults";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TuningProposalEditor } from "./TuningProposalEditor";

import { TuningFlaggedRuns } from "./TuningFlaggedRuns";
import { TuneHeader } from "@/components/agents/TuneHeader";
import {
	TONE_MUTED,
	TYPE_MUTED,
	TYPE_PANE_LABEL,
} from "@/components/agents/design-tokens";

import { useAgent } from "@/hooks/useAgents";
import { useInfiniteAgentRuns } from "@/services/agentRuns";
import { useAgentStats } from "@/services/agents";
import {
	useApplyTuning,
	useTuningDryRun,
	useTuningSession,
	type ConsolidatedDryRunResponse,
	type ConsolidatedProposal,
} from "@/services/agentTuning";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/v1";

type AgentRun = components["schemas"]["AgentRunResponse"];

export function AgentTuneWorkbench() {
	const { id: agentId } = useParams<{ id: string }>();

	const {
		data: agent,
		isLoading: agentLoading,
		isError: agentError,
		isFetching: agentFetching,
		refetch: refetchAgent,
	} = useAgent(agentId);
	const {
		data: stats,
		isLoading: statsLoading,
		isError: statsError,
		isFetching: statsFetching,
		refetch: refetchStats,
	} = useAgentStats(agentId);
	const {
		data: flaggedResp,
		isLoading: flaggedLoading,
		isError: flaggedReadError,
		isFetching: flaggedFetching,
		refetch: refetchFlagged,
		hasNextPage,
		fetchNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = useInfiniteAgentRuns({
		agentId,
		verdict: "down",
	});

	const tuningSession = useTuningSession();
	const applyTuning = useApplyTuning();
	const tuningDryRun = useTuningDryRun();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	const flagged: AgentRun[] = (flaggedResp?.pages.flatMap(
		(page) => page.items,
	) ?? []) as AgentRun[];
	const flaggedTotal = flaggedResp?.pages[0]?.total ?? flagged.length;
	const flaggedError = flaggedReadError && !isFetchNextPageError;
	const hasFlaggedRuns = flagged.length > 0;
	const busy =
		tuningSession.isPending ||
		tuningDryRun.isPending ||
		applyTuning.isPending;
	const canGenerate = hasFlaggedRuns && !busy && !flaggedError && !agentError;

	const [proposal, setProposal] = useState<ConsolidatedProposal | null>(null);
	const [edits, setEdits] = useState<string>("");
	const [currentOpen, setCurrentOpen] = useState(false);
	const [dryRun, setDryRun] = useState<ConsolidatedDryRunResponse | null>(
		null,
	);

	const [actionError, setActionError] = useState<{
		action: "generate" | "dry-run" | "apply";
		message: string;
	} | null>(null);
	const currentPrompt = agent?.system_prompt ?? "";

	function handleGenerate() {
		if (!agentId || !canGenerate) return;
		setActionError(null);
		tuningSession.mutate(
			{ params: { path: { agent_id: agentId } } },
			{
				onSuccess: (data) => {
					setProposal(data);
					setEdits(data.proposed_prompt);
					setDryRun(null);
				},
				onError: () =>
					setActionError({
						action: "generate",
						message:
							"Could not generate a proposal. Your existing edits are preserved. Try Generate proposal again.",
					}),
			},
		);
	}

	function handleDiscard() {
		if (busy) return;
		setActionError(null);
		setProposal(null);
		setEdits("");
		setDryRun(null);
	}

	function handleDryRun() {
		if (!agentId || !edits.trim() || busy) return;
		setActionError(null);
		tuningDryRun.mutate(
			{
				params: { path: { agent_id: agentId } },
				body: { proposed_prompt: edits },
			},
			{
				onSuccess: (data) => {
					setDryRun(data);
				},
				onError: () =>
					setActionError({
						action: "dry-run",
						message:
							"Could not complete the dry-run. Your proposal is preserved. Try Run dry-run again.",
					}),
			},
		);
	}

	function handleApply() {
		if (!agentId || !edits.trim() || busy) return;
		setActionError(null);
		applyTuning.mutate(
			{
				params: { path: { agent_id: agentId } },
				body: { new_prompt: edits },
			},
			{
				onSuccess: async () => {
					toast.success("Prompt updated");
					await Promise.all([
						queryClient.invalidateQueries({
							queryKey: ["get", "/api/agents"],
						}),
						queryClient.invalidateQueries({
							queryKey: [
								"get",
								"/api/agents/{agent_id}",
								{ params: { path: { agent_id: agentId } } },
							],
						}),
						queryClient.invalidateQueries({
							queryKey: ["get", "/api/agents/{agent_id}/stats"],
						}),
						queryClient.invalidateQueries({
							queryKey: ["get", "/api/agents/stats/fleet"],
						}),
						queryClient.invalidateQueries({
							queryKey: ["agent-runs"],
						}),
						queryClient.invalidateQueries({
							queryKey: ["agent-runs-infinite"],
						}),
					]);
					navigate(`/agents/${agentId}`);
				},
				onError: () =>
					setActionError({
						action: "apply",
						message:
							"Could not confirm the prompt update. Your proposal is preserved. Try Apply live again.",
					}),
			},
		);
	}

	if (!agent && agentLoading) return <PageLoader />;
	if (!agent && agentError)
		return (
			<div className="space-y-4">
				<h1 className="font-display text-2xl font-semibold">
					Tune agent
				</h1>
				<FleetReadError
					resource="agent"
					cached={false}
					pending={agentFetching}
					onRetry={() => {
						void refetchAgent();
					}}
				/>
			</div>
		);

	return (
		<div
			className="mx-auto flex min-w-0 w-full max-w-[1400px] flex-col gap-5"
			data-testid="agent-tune-workbench"
		>
			<TuneHeader
				agentId={agentId}
				agentName={agent?.name}
				flaggedCount={flaggedTotal}
				stats={stats ?? null}
				statsLoading={statsLoading}
				action={
					<Button
						type="button"
						variant="outline"
						size="sm"
						data-testid="dryrun-button"
						disabled={!proposal || !edits.trim() || busy}
						onClick={handleDryRun}
					>
						{tuningDryRun.isPending ? (
							<Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
						) : (
							<PlayCircle className="h-3.5 w-3.5" />
						)}
						Run dry-run
					</Button>
				}
			/>

			{agentError && (
				<FleetReadError
					resource="agent"
					cached={!!agent}
					pending={agentFetching}
					onRetry={() => {
						void refetchAgent();
					}}
				/>
			)}
			{statsError && (
				<FleetReadError
					resource="agent statistics"
					cached={!!stats}
					pending={statsFetching}
					onRetry={() => {
						void refetchStats();
					}}
				/>
			)}
			{actionError?.action === "dry-run" && (
				<TuningActionError message={actionError.message} />
			)}

			{/* Dry-run results (full-width, appears after first run) */}
			{dryRun ? <TuningDryRunResults {...dryRun} /> : null}

			<div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
				{/* Left: flagged runs */}
				<div
					className="flex min-w-0 flex-col gap-3"
					data-testid="tune-pane-flagged"
				>
					<TuningFlaggedRuns
						runs={flagged}
						total={flaggedTotal}
						loading={flaggedLoading}
						error={flaggedError}
						cached={!!flaggedResp}
						fetching={flaggedFetching}
						onRetry={() => void refetchFlagged()}
						hasMore={hasNextPage}
						loadingMore={isFetchingNextPage}
						moreError={isFetchNextPageError}
						onLoadMore={() => void fetchNextPage()}
					/>
					<Button
						type="button"
						data-testid="generate-proposal-button"
						className="min-h-11 h-auto whitespace-normal py-2"
						disabled={!canGenerate}
						onClick={handleGenerate}
					>
						{tuningSession.isPending ? (
							<Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
						) : (
							<Sparkles className="h-3.5 w-3.5" />
						)}
						{proposal
							? "Re-generate"
							: `Generate proposal from ${flaggedTotal} run${flaggedTotal === 1 ? "" : "s"}`}
					</Button>
					{actionError?.action === "generate" && (
						<TuningActionError message={actionError.message} />
					)}
				</div>

				{/* Center: prompt editor */}
				<div
					className="flex min-w-0 flex-col gap-3"
					data-testid="tune-pane-editor"
				>
					<div className={TYPE_PANE_LABEL}>Prompt editor</div>

					{/* Current prompt (collapsible) */}
					<div className="overflow-hidden rounded-[var(--bf-radius-surface)] border bg-card">
						<button
							type="button"
							data-testid="current-prompt-toggle"
							onClick={() => setCurrentOpen((o) => !o)}
							className="flex min-h-11 w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm"
							aria-expanded={currentOpen}
						>
							<span className="font-medium">Current prompt</span>
							<ChevronDown
								className={cn(
									"h-3 w-3 transition-transform motion-reduce:transition-none",
									currentOpen ? "rotate-0" : "-rotate-90",
								)}
							/>
						</button>
						{currentOpen ? (
							<pre className="max-h-60 overflow-y-auto whitespace-pre-wrap [overflow-wrap:anywhere] border-t px-4 py-3 font-mono text-sm text-muted-foreground">
								{currentPrompt || "(no system prompt set)"}
							</pre>
						) : null}
					</div>

					{/* Proposed prompt */}
					{tuningSession.isPending ? (
						<div className="rounded-[var(--bf-radius-surface)] border bg-card p-4">
							<div className={cn("mb-2 text-xs", TONE_MUTED)}>
								Building proposal…
							</div>
							<Skeleton className="h-32 w-full" />
						</div>
					) : !proposal ? (
						<div
							data-testid="editor-empty-state"
							className={cn(
								"rounded-[var(--bf-radius-surface)] border border-dashed p-6 text-center",
								TYPE_MUTED,
								TONE_MUTED,
							)}
						>
							Select{" "}
							<span className="font-medium">
								Generate proposal
							</span>{" "}
							to read the flagged runs and suggest one
							consolidated prompt change.
						</div>
					) : (
						<TuningProposalEditor
							currentPrompt={currentPrompt}
							edits={edits}
							summary={proposal.summary}
							error={
								actionError?.action === "apply"
									? actionError.message
									: undefined
							}
							busy={busy}
							applying={applyTuning.isPending}
							onChange={(value) => {
								setEdits(value);
								setDryRun(null);
							}}
							onDiscard={handleDiscard}
							onApply={handleApply}
						/>
					)}
				</div>
			</div>
		</div>
	);
}

export default AgentTuneWorkbench;
