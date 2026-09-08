import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import type { SchedulerTaskHistoryResponse } from "@/services/schedulerDiagnostics";

type SchedulerLog =
	SchedulerTaskHistoryResponse["runs"][number]["logs"][number];

export function SchedulerLogRecord({ log }: { log: SchedulerLog }) {
	return (
		<li className="space-y-2 border-b py-4 last:border-b-0">
			<div className="flex flex-wrap items-center gap-x-3 gap-y-2">
				<Badge
					variant={log.level === "error" ? "destructive" : "outline"}
					className={
						log.level === "warning"
							? "bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]"
							: undefined
					}
				>
					{log.level.charAt(0).toUpperCase() + log.level.slice(1)}
				</Badge>
				<time
					dateTime={log.created_at}
					className="text-xs text-muted-foreground"
				>
					{format(new Date(log.created_at), "MMM d, h:mm:ss a")}
				</time>
			</div>
			<p className="whitespace-pre-wrap text-sm [overflow-wrap:anywhere]">
				{log.message}
			</p>
			<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
				{log.code}
			</p>
		</li>
	);
}
