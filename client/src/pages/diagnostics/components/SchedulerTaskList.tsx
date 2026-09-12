import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import type { SchedulerTaskStatus } from "@/services/schedulerDiagnostics";
function formatBytes(value: number) {
	const units = ["B", "KiB", "MiB", "GiB", "TiB"];
	let amount = value;
	let unit = 0;
	while (amount >= 1024 && unit < units.length - 1) {
		amount /= 1024;
		unit += 1;
	}
	return `${amount >= 10 || unit === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[unit]}`;
}
function relativeTime(value: string | null | undefined) {
	if (!value) return "Never";
	return formatDistanceToNow(new Date(value), { addSuffix: true });
}

function statusVariant(status: string | undefined) {
	if (status === "failed" || status === "cancelled")
		return "destructive" as const;
	if (
		[
			"queued",
			"running",
			"enqueued",
			"waiting",
			"cancel_requested",
		].includes(status ?? "")
	)
		return "outline" as const;
	if (status === "succeeded") return "secondary" as const;
	return "outline" as const;
}

function statusClassName(status: string | undefined) {
	if (status === "succeeded") {
		return "border-[var(--bf-success)]/30 bg-[var(--bf-success)]/10 text-[var(--bf-success)]";
	}
	if (
		[
			"queued",
			"running",
			"enqueued",
			"waiting",
			"cancel_requested",
		].includes(status ?? "")
	) {
		return "border-[var(--bf-warning)]/30 bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]";
	}
	return undefined;
}

function formatStatus(status: string | undefined) {
	if (!status) return "Not run";
	return status
		.split("_")
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(" ");
}

function containerMemoryChange(
	startBytes: number | null | undefined,
	peakBytes: number | null | undefined,
) {
	if (startBytes == null || peakBytes == null) return null;
	return Math.max(0, peakBytes - startBytes);
}

function formatContainerMemoryChange(
	startBytes: number | null | undefined,
	peakBytes: number | null | undefined,
) {
	const change = containerMemoryChange(startBytes, peakBytes);
	return change == null ? "—" : formatBytes(change);
}

export function SchedulerTaskList({
	tasks,
	onSelect,
}: {
	tasks: SchedulerTaskStatus[];
	onSelect: (task: SchedulerTaskStatus) => void;
}) {
	return (
		<div className="@container min-w-0">
			<ul aria-label="System schedules" className="space-y-3 @4xl:hidden">
				{tasks.map((task) => (
					<li
						key={task.task_id}
						className="rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)] space-y-4"
					>
						<div className="space-y-2">
							<h4 className="font-semibold [overflow-wrap:anywhere]">
								{task.name}
							</h4>
							<p className="text-xs text-muted-foreground">
								{task.execution_mode === "durable_job"
									? "Distributed Job"
									: "Leader Trigger"}
							</p>
							<Badge
								variant={statusVariant(
									task.last_run?.platform_job_status ??
										task.last_run?.status,
								)}
								className={statusClassName(
									task.last_run?.platform_job_status ??
										task.last_run?.status,
								)}
							>
								{formatStatus(
									task.last_run?.platform_job_status ??
										task.last_run?.status,
								)}
							</Badge>
						</div>
						{task.last_run?.error_message && (
							<p className="text-sm text-destructive [overflow-wrap:anywhere]">
								{task.last_run.error_message}
							</p>
						)}
						<dl className="grid gap-3 text-sm">
							<div>
								<dt className="text-xs text-muted-foreground">
									Schedule
								</dt>
								<dd className="[overflow-wrap:anywhere]">
									{task.schedule}
								</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									Next run
								</dt>
								<dd>{relativeTime(task.next_run_at)}</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									Last run
								</dt>
								<dd>
									{relativeTime(task.last_run?.completed_at)}
									{task.last_run?.duration_ms != null &&
										` · ${task.last_run.duration_ms} ms`}
								</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									Container memory change
								</dt>
								<dd>
									{formatContainerMemoryChange(
										task.last_run
											?.platform_job_memory_start_bytes,
										task.last_run
											?.platform_job_memory_peak_bytes,
									)}
								</dd>
							</div>
						</dl>
						<Button
							type="button"
							variant="outline"
							className="min-h-11 w-full"
							aria-label={`View recent runs for ${task.name}`}
							onClick={() => onSelect(task)}
						>
							View recent runs
						</Button>
					</li>
				))}
			</ul>
			<DataTable
				className={tasks.length === 0 ? "hidden" : "hidden @4xl:block"}
			>
				<DataTableHeader>
					<DataTableRow>
						<DataTableHead>Name</DataTableHead>
						<DataTableHead>State</DataTableHead>
						<DataTableHead>Schedule</DataTableHead>
						<DataTableHead>Next Run</DataTableHead>
						<DataTableHead>Last Run</DataTableHead>
						<DataTableHead title="Change in the shared scheduler container working set while this job ran">
							Memory
						</DataTableHead>
					</DataTableRow>
				</DataTableHeader>
				<DataTableBody>
					{tasks.map((task) => (
						<DataTableRow
							key={task.task_id}
							clickable
							className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
							tabIndex={0}
							aria-label={`View recent runs for ${task.name}`}
							onClick={() => onSelect(task)}
							onKeyDown={(event) => {
								if (
									event.key === "Enter" ||
									event.key === " "
								) {
									event.preventDefault();
									onSelect(task);
								}
							}}
						>
							<DataTableCell>
								<div className="font-medium">{task.name}</div>
								<div className="text-xs text-muted-foreground">
									{task.execution_mode === "durable_job"
										? "Distributed Job"
										: "Leader Trigger"}
								</div>
							</DataTableCell>
							<DataTableCell>
								<Badge
									variant={statusVariant(
										task.last_run?.platform_job_status ??
											task.last_run?.status,
									)}
									className={statusClassName(
										task.last_run?.platform_job_status ??
											task.last_run?.status,
									)}
								>
									{formatStatus(
										task.last_run?.platform_job_status ??
											task.last_run?.status,
									)}
								</Badge>
								{task.last_run?.error_message && (
									<div
										className="mt-1 max-w-[260px] truncate text-xs text-destructive"
										title={task.last_run.error_message}
									>
										{task.last_run.error_message}
									</div>
								)}
							</DataTableCell>
							<DataTableCell>
								<div>{task.schedule}</div>
							</DataTableCell>
							<DataTableCell>
								{relativeTime(task.next_run_at)}
							</DataTableCell>
							<DataTableCell>
								<div>
									{task.last_run?.duration_ms == null
										? "—"
										: `${task.last_run.duration_ms} ms`}
								</div>
								<div className="text-xs text-muted-foreground">
									{relativeTime(task.last_run?.completed_at)}
								</div>
							</DataTableCell>
							<DataTableCell>
								{formatContainerMemoryChange(
									task.last_run
										?.platform_job_memory_start_bytes,
									task.last_run
										?.platform_job_memory_peak_bytes,
								)}
							</DataTableCell>
						</DataTableRow>
					))}
				</DataTableBody>
			</DataTable>
		</div>
	);
}
