import type { ReactNode } from "react";
import { RunStatusBadge } from "./RunStatusBadge";
import { formatDate, formatRelativeTime } from "@/lib/utils";
import type { components } from "@/lib/v1";

type ExecutionStatus =
	| components["schemas"]["ExecutionStatus"]
	| "Cancelling"
	| "Cancelled";

interface ExecutionMetadataBarProps {
	workflowName: string;
	status: ExecutionStatus;
	executedByName?: string | null;
	orgName?: string | null;
	startedAt?: string | null;
	durationMs?: number | null;
	totalDurationMs?: number | null;
	queuePosition?: number;
	waitReason?: string;
	availableMemoryMb?: number;
	requiredMemoryMb?: number;
}

function formatDuration(ms: number): string {
	if (ms < 1000) return `${ms}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
	const minutes = Math.floor(ms / 60000);
	const seconds = ((ms % 60000) / 1000).toFixed(0);
	return `${minutes}m ${seconds}s`;
}

export function ExecutionMetadataBar({
	workflowName,
	status,
	executedByName,
	orgName,
	startedAt,
	durationMs,
	totalDurationMs,
	queuePosition,
	waitReason,
	availableMemoryMb,
	requiredMemoryMb,
}: ExecutionMetadataBarProps) {
	const active = status === "Running" || status === "Cancelling";
	const waiting = status === "Pending" || status === "Scheduled";
	return (
		<section aria-label="Execution metadata" className="@container min-w-0 space-y-4">
			<div className="flex min-w-0 flex-col items-start gap-2">
				<h3 className="min-w-0 font-display text-xl font-semibold leading-tight [overflow-wrap:anywhere]">{workflowName}</h3>
				<RunStatusBadge status={status} queuePosition={queuePosition} waitReason={waitReason} availableMemoryMb={availableMemoryMb} requiredMemoryMb={requiredMemoryMb} />
			</div>
			<dl className="grid min-w-0 grid-cols-1 gap-3 border-t pt-4 @md:grid-cols-2 @md:gap-x-6">
				<MetadataField label="Executed by">{executedByName || "Unknown"}</MetadataField>
				<MetadataField label="Organization">{orgName || "Global"}</MetadataField>
				<MetadataField label="Started">
					{startedAt ? <><time dateTime={startedAt}>{formatDate(startedAt)}</time><span className="block text-xs text-muted-foreground">{formatRelativeTime(startedAt)}</span></> : "Not started"}
				</MetadataField>
				{totalDurationMs != null && <MetadataField label="Total" description="Total platform time from worker start through persisted completion">{formatDuration(totalDurationMs)}</MetadataField>}
				<MetadataField label="Workflow" description="Time spent executing workflow code">
					{durationMs != null ? formatDuration(durationMs) : active ? "In progress..." : waiting ? "Not started" : "Not available"}
				</MetadataField>
			</dl>
		</section>
	);
}

function MetadataField({ label, description, children }: { label: string; description?: string; children: ReactNode }) {
	return <div className="min-w-0 space-y-1">
		<dt className="text-xs text-muted-foreground" title={description}>{label}</dt>
		<dd className="min-w-0 text-sm [overflow-wrap:anywhere]">{children}</dd>
	</div>;
}
