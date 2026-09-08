import { Link } from "react-router-dom";
import {
	AlertCircle,
	CheckCircle,
	Loader2,
	RefreshCw,
	ThumbsDown,
	ThumbsUp,
	XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, formatDuration } from "@/lib/utils";
import type { AgentRunNavigationState } from "@/lib/agent-run-navigation";
import type { components } from "@/lib/v1";

type AgentRun = components["schemas"]["AgentRunResponse"];

export function RunStatusBadge({ status }: { status: string }) {
	switch (status) {
		case "completed":
			return (
				<Badge
					variant="default"
					className="bg-[var(--bf-success)]/10 text-[var(--bf-success)]"
				>
					<CheckCircle className="h-3 w-3" /> Completed
				</Badge>
			);
		case "failed":
			return (
				<Badge variant="destructive">
					<XCircle className="h-3 w-3" /> Failed
				</Badge>
			);
		case "running":
			return (
				<Badge variant="secondary">
					<Loader2 className="h-3 w-3 animate-spin motion-reduce:animate-none" />{" "}
					Running
				</Badge>
			);
		case "budget_exceeded":
			return (
				<Badge
					variant="warning"
					className="bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]"
				>
					<AlertCircle className="h-3 w-3" /> Budget exceeded
				</Badge>
			);
		default:
			return <Badge variant="outline">{status}</Badge>;
	}
}

export function VerdictGlyph({ verdict }: { verdict: AgentRun["verdict"] }) {
	if (verdict === "up") {
		return (
			<ThumbsUp
				className="h-3 w-3 text-[var(--bf-success)]"
				aria-label="Approved"
			/>
		);
	}
	if (verdict === "down") {
		return (
			<ThumbsDown
				className="h-3 w-3 text-[var(--bf-danger)]"
				aria-label="Flagged"
			/>
		);
	}
	return null;
}

interface AgentRunRecordProps {
	run: AgentRun;
	navigationState: AgentRunNavigationState;
	isRerunning: boolean;
	onRerun: (runId: string) => void;
}

export function AgentRunRecord({
	run,
	navigationState,
	isRerunning,
	onRerun,
}: AgentRunRecordProps) {
	return (
		<li className="min-w-0 space-y-3 p-4" data-testid="agent-run-record">
			<RunStatusBadge status={run.status} />
			<Link
				to={`/agents/${run.agent_id}/runs/${run.id}`}
				state={navigationState}
				className="flex min-h-11 items-center rounded-[var(--bf-radius-control)] text-sm font-semibold [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				{run.agent_name ?? "Agent"}
			</Link>
			<p className="text-sm [overflow-wrap:anywhere]">
				{run.asked || run.did || "No summary available."}
			</p>
			<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
				<dt className="text-muted-foreground">Started</dt>
				<dd>
					{run.started_at
						? formatDate(run.started_at)
						: "Not started"}
				</dd>
				<dt className="text-muted-foreground">Duration</dt>
				<dd className="tabular-nums">
					{run.duration_ms != null
						? formatDuration(run.duration_ms)
						: "Not available"}
				</dd>
				<dt className="text-muted-foreground">Review</dt>
				<dd className="flex items-center gap-1.5">
					<VerdictGlyph verdict={run.verdict} />
					{run.verdict === "up"
						? "Approved"
						: run.verdict === "down"
							? "Flagged"
							: "Not reviewed"}
				</dd>
			</dl>
			<Button
				variant="outline"
				className="min-h-11"
				data-testid={`rerun-${run.id}`}
				disabled={isRerunning}
				onClick={() => onRerun(run.id)}
			>
				<RefreshCw className="h-4 w-4" />
				Rerun with same input
			</Button>
		</li>
	);
}
