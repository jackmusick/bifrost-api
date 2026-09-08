import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/v1";
import { formatDate } from "@/lib/utils";

type LogListEntry = components["schemas"]["LogListEntry"];

export function LogLevel({ level }: { level: string }) {
	const severity = level.toUpperCase();
	const toneClass =
		severity === "ERROR" || severity === "CRITICAL"
			? "border-[var(--bf-danger)]/30 bg-[var(--bf-danger)]/10 text-[var(--bf-danger)]"
			: severity === "WARNING"
				? "border-[var(--bf-warning)]/30 bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]"
				: severity === "SUCCESS"
					? "border-[var(--bf-success)]/30 bg-[var(--bf-success)]/10 text-[var(--bf-success)]"
					: severity === "INFO"
						? "border-[var(--bf-info)]/30 bg-[var(--bf-info)]/10 text-[var(--bf-info)]"
						: "";
	return (
		<Badge
			variant={
				severity === "ERROR" || severity === "CRITICAL"
					? "destructive"
					: "outline"
			}
			className={`h-auto whitespace-normal font-mono text-xs uppercase [overflow-wrap:anywhere] ${toneClass}`}
		>
			{level}
		</Badge>
	);
}

export function LogRecord({
	log,
	onOpen,
}: {
	log: LogListEntry;
	onOpen: (log: LogListEntry) => void;
}) {
	return (
		<li data-testid="log-record" className="min-w-0 space-y-3 p-4">
			<LogLevel level={log.level} />
			<a
				href={`/history/${log.execution_id}`}
				className="flex min-h-11 items-center rounded-[var(--bf-radius-control)] font-mono text-sm font-medium [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
					onOpen(log);
				}}
			>
				{log.workflow_name}
			</a>
			<p className="whitespace-pre-wrap font-mono text-sm leading-relaxed [overflow-wrap:anywhere]">
				{log.message}
			</p>
			<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
				<dt className="text-muted-foreground">Organization</dt>
				<dd className="[overflow-wrap:anywhere]">
					{log.organization_name || "—"}
				</dd>
				<dt className="text-muted-foreground">Timestamp</dt>
				<dd>{formatDate(log.timestamp)}</dd>
			</dl>
		</li>
	);
}
