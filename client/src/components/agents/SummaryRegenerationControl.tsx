import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useRegenerateSummary } from "@/services/agentRuns";

/** Shared request and recovery UI for run summaries in pages, drawers and review. */
export function SummaryRegenerationControl({
	runId,
	allowed,
	testId,
}: {
	runId: string;
	allowed: boolean;
	testId: string;
}) {
	const mutation = useRegenerateSummary();
	const queryClient = useQueryClient();
	const busy = useRef(false);
	const [failedRun, setFailedRun] = useState<string | null>(null);
	const errorRef = useRef<HTMLDivElement>(null);
	const failed = failedRun === runId;
	useEffect(() => {
		if (failed) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView?.({ block: "nearest" });
		}
	}, [failed]);
	function regenerate() {
		if (!allowed || busy.current) return;
		busy.current = true;
		setFailedRun(null);
		mutation.mutate(
			{ params: { path: { run_id: runId } } },
			{
				onSuccess: () => {
					toast.success("Summary regeneration queued");
					void queryClient.invalidateQueries({
						queryKey: ["get", "/api/agent-runs/{run_id}"],
					});
					void queryClient.invalidateQueries({
						queryKey: ["agent-runs"],
					});
					void queryClient.invalidateQueries({
						queryKey: ["agent-runs-infinite"],
					});
				},
				onError: () => setFailedRun(runId),
				onSettled: () => {
					busy.current = false;
				},
			},
		);
	}
	return (
		<div className="min-w-0 space-y-2">
			<Button
				variant="outline"
				size="sm"
				className="min-h-11"
				disabled={!allowed || mutation.isPending}
				onClick={regenerate}
				data-testid={testId}
				title={
					allowed
						? "Re-run summarization"
						: "Only platform admins can regenerate summaries"
				}
			>
				{mutation.isPending ? (
					<Loader2 className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
				) : (
					<RefreshCw className="h-3.5 w-3.5" />
				)}
				{failed ? "Retry regeneration" : "Regenerate"}
			</Button>
			{mutation.isPending ? (
				<p role="status" className="text-xs text-muted-foreground">
					Queuing summary…
				</p>
			) : null}
			{failed ? (
				<div
					ref={errorRef}
					tabIndex={-1}
					role="alert"
					className="rounded-[var(--bf-radius-control)] border bg-[var(--bf-warning-soft)] p-3 text-xs"
				>
					Could not queue the summary. Try regenerating again.
				</div>
			) : null}
		</div>
	);
}
