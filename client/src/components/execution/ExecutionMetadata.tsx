import type { ReactNode } from "react";
import { formatDate, formatDuration, formatRelativeTime } from "@/lib/utils";

interface ExecutionMetadataProps {
	executedByName?: string | null;
	orgName?: string | null;
	scheduledAt?: string | null;
	startedAt?: string | null;
	completedAt?: string | null;
	durationMs?: number | null;
}

export function ExecutionMetadata({
	executedByName,
	orgName,
	scheduledAt,
	startedAt,
	completedAt,
	durationMs,
}: ExecutionMetadataProps) {
	return (
		<dl className="@container min-w-0 divide-y divide-border rounded-[var(--bf-radius-surface)] border border-border bg-muted/50 text-sm">
			<MetadataRow label="Run by">
				{executedByName || "Unknown"}
			</MetadataRow>
			<MetadataRow label="Scope">{orgName || "Global"}</MetadataRow>
			{scheduledAt && (
				<MetadataRow label="Scheduled for">
					<time dateTime={scheduledAt}>
						{formatDate(scheduledAt)}
					</time>
				</MetadataRow>
			)}
			<MetadataRow
				label="Started"
				title={startedAt ? formatDate(startedAt) : undefined}
			>
				{startedAt ? (
					<ExecutionTime value={startedAt} />
				) : (
					"Not started"
				)}
			</MetadataRow>
			{completedAt && (
				<MetadataRow label="Completed" title={formatDate(completedAt)}>
					<ExecutionTime value={completedAt} />
				</MetadataRow>
			)}
			{durationMs != null && (
				<MetadataRow label="Duration">
					<span className="font-mono tabular-nums">
						{formatDuration(durationMs)}
					</span>
				</MetadataRow>
			)}
		</dl>
	);
}

function MetadataRow({
	label,
	title,
	children,
}: {
	label: string;
	title?: string;
	children: ReactNode;
}) {
	return (
		<div className="grid min-w-0 gap-1 px-3 py-3 @sm:grid-cols-[6rem_minmax(0,1fr)] @sm:gap-3">
			<dt className="text-sm text-muted-foreground">{label}</dt>
			<dd title={title} className="min-w-0 [overflow-wrap:anywhere]">
				{children}
			</dd>
		</div>
	);
}

function ExecutionTime({ value }: { value: string }) {
	return (
		<div className="space-y-1">
			<p>{formatRelativeTime(value)}</p>
			<time
				dateTime={value}
				className="block text-sm text-muted-foreground"
			>
				{formatDate(value)}
			</time>
		</div>
	);
}
