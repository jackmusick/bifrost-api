import type { AuditLogEntry } from "@/hooks/useAuditLog";
import { AuditOutcome } from "./AuditOutcome";

export function AuditEventCards({
	entries,
	context,
}: {
	entries: AuditLogEntry[];
	context: (entry: AuditLogEntry) => string;
}) {
	return (
		<ol aria-label="Audit events" className="space-y-3">
			{entries.map((entry) => (
				<li
					key={entry.id}
					className="min-w-0 rounded-[var(--bf-radius-surface)] border bg-card p-4 [overflow-wrap:anywhere]"
				>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<h2 className="min-w-0 text-sm font-semibold">
							{entry.action}
						</h2>
						<AuditOutcome outcome={entry.outcome} />
					</div>
					<time
						dateTime={entry.timestamp}
						className="mt-2 block text-xs text-muted-foreground"
					>
						{new Date(entry.timestamp).toLocaleString()}
					</time>
					<dl className="mt-4 space-y-3 text-sm">
						{[
							[
								"Actor",
								entry.actor.user_email ||
									entry.actor.user_name ||
									(entry.source !== "http"
										? `(${entry.source})`
										: "(unauthenticated)"),
							],
							[
								"Resource",
								entry.resource_type
									? `${entry.resource_type}${entry.resource_id ? ` / ${entry.resource_id}` : ""}`
									: "—",
							],
							["Context", context(entry)],
							["IP address", entry.ip_address || "—"],
						].map(([label, value]) => (
							<div key={label}>
								<dt className="text-xs text-muted-foreground">
									{label}
								</dt>
								<dd className="mt-1 whitespace-pre-wrap">
									{value}
								</dd>
							</div>
						))}
					</dl>
				</li>
			))}
		</ol>
	);
}
