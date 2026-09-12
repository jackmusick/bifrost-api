import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { PlatformJob } from "@/services/platformJobs";

export function PlatformJobRecord({
	job,
	status,
	memory,
	elapsed,
	onSelect,
}: {
	job: PlatformJob;
	status: ReactNode;
	memory: ReactNode;
	elapsed: ReactNode;
	onSelect: () => void;
}) {
	return (
		<li className="space-y-4 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]">
			<div className="space-y-2">
				<h4 className="font-semibold [overflow-wrap:anywhere]">
					{job.title}
				</h4>
				<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
					{job.job_type}
				</p>
				{status}
			</div>
			<p className="text-sm [overflow-wrap:anywhere]">
				{job.progress.phase ?? "No phase reported"}
			</p>
			{job.progress.percent != null &&
				["queued", "running", "waiting", "cancel_requested"].includes(
					job.status,
				) && (
					<div className="flex items-center gap-3">
						<Progress
							aria-label={`${job.title} progress`}
							value={job.progress.percent}
							className="flex-1"
						/>
						<span className="text-xs tabular-nums">
							{job.progress.percent.toFixed(0)}%
						</span>
					</div>
				)}
			{job.error && (
				<p className="text-sm text-destructive [overflow-wrap:anywhere]">
					{job.error.message}
				</p>
			)}
			<dl className="grid gap-3 text-sm">
				<div>
					<dt className="text-xs text-muted-foreground">
						Requested by
					</dt>
					<dd className="[overflow-wrap:anywhere]">
						{job.requested_by_name || "Unavailable"}
					</dd>
				</div>
				<div>
					<dt className="text-xs text-muted-foreground">Elapsed</dt>
					<dd>{elapsed}</dd>
				</div>
				<div>
					<dt className="text-xs text-muted-foreground">Memory</dt>
					<dd>{memory}</dd>
				</div>
			</dl>
			<Button
				type="button"
				variant="outline"
				className="min-h-11 w-full"
				aria-label={`View ${job.title} platform job`}
				onClick={onSelect}
			>
				View job details
			</Button>
		</li>
	);
}
