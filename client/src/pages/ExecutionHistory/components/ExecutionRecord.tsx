import type { ReactNode } from "react";
import { RunStatusBadge } from "@/components/execution";
import type { components } from "@/lib/v1";
import { formatRunDuration, formatRunTime } from "./historyView";

type ExecutionSummary = components["schemas"]["ExecutionSummary"];
interface ExecutionRecordProps {
	execution: ExecutionSummary;
	status: ExecutionSummary["status"] | "Cancelled";
	organizationName?: string;
	onOpen: () => void;
	actions: ReactNode;
}

export function ExecutionRecord({
	execution,
	status,
	organizationName,
	onOpen,
	actions,
}: ExecutionRecordProps) {
	const anchorIso =
		execution.started_at ??
		execution.scheduled_at ??
		execution.completed_at;
	return (
		<li data-testid="execution-record" className="min-w-0 space-y-3 p-4">
			<RunStatusBadge
				status={status}
				scheduledAt={execution.scheduled_at}
			/>
			<a
				href={`/history/${execution.execution_id}`}
				onClick={(event) => {
					if (
						event.metaKey ||
						event.ctrlKey ||
						event.shiftKey ||
						event.altKey ||
						event.button !== 0
					)
						return;
					event.preventDefault();
					onOpen();
				}}
				className="flex min-h-11 items-center font-mono text-sm font-medium [overflow-wrap:anywhere] rounded-[var(--bf-radius-control)] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				{execution.workflow_name}
			</a>
			<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
				{organizationName !== undefined && (
					<>
						<dt className="text-muted-foreground">Organization</dt>
						<dd className="[overflow-wrap:anywhere]">
							{organizationName}
						</dd>
					</>
				)}
				<dt className="text-muted-foreground">Run by</dt>
				<dd className="[overflow-wrap:anywhere]">
					{execution.executed_by_name}
				</dd>
				<dt className="text-muted-foreground">
					{status === "Scheduled" ? "Scheduled" : "Started"}
				</dt>
				<dd>{anchorIso ? formatRunTime(anchorIso) : "Not started"}</dd>
				<dt className="text-muted-foreground">Duration</dt>
				<dd className="tabular-nums">
					{formatRunDuration(
						execution.started_at,
						execution.completed_at,
					) ?? "Not available"}
				</dd>
			</dl>
			{execution.error_message &&
				["Failed", "Timeout", "CompletedWithErrors"].includes(
					status,
				) && (
					<p className="text-sm text-destructive [overflow-wrap:anywhere]">
						{execution.error_message}
					</p>
				)}
			{actions}
		</li>
	);
}
