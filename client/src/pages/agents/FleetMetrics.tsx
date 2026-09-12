import type { FleetStats } from "@/services/agents";
import { Skeleton } from "@/components/ui/skeleton";
import { CARD_SURFACE } from "@/components/agents/design-tokens";
import { cn, formatCost, formatNumber } from "@/lib/utils";

export function FleetMetrics({
	stats,
	loading,
	scopeLabel,
	agentLabel,
}: {
	stats?: FleetStats;
	loading: boolean;
	scopeLabel: string;
	agentLabel: string;
}) {
	const metrics = stats
		? [
				{
					label: "Runs (7d)",
					value: formatNumber(stats.total_runs),
					detail: stats.total_runs
						? "Runs and conversations"
						: "No runs yet",
				},
				{
					label: "Success rate",
					value: `${Math.round((stats.avg_success_rate ?? 0) * 100)}%`,
					detail: "Completed runs",
				},
				{
					label: "Spend (7d)",
					value: formatCost(stats.total_cost_7d),
					detail: stats.total_runs
						? `${formatCost(Number(stats.total_cost_7d) / 7)}/day avg`
						: "No spend yet",
				},
				{
					label: `Active ${agentLabel}`,
					value: formatNumber(stats.active_agents),
					detail: scopeLabel,
				},
				{
					label: "Needs review",
					value: formatNumber(stats.needs_review),
					detail: stats.needs_review
						? "Flagged runs"
						: "No flagged runs",
					alert: stats.needs_review > 0,
				},
			]
		: [];
	return (
		<section
			aria-label="Fleet statistics"
			aria-busy={loading || !stats}
			className="space-y-2"
		>
			<p className="text-xs text-muted-foreground">
				Fleet totals · {scopeLabel} · Last 7 days
			</p>
			{loading || !stats ? (
				<div
					className="grid grid-cols-1 min-[400px]:grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5"
					role="status"
					aria-label="Loading fleet statistics"
				>
					{Array.from({ length: 5 }, (_, i) => (
						<Skeleton key={i} className="h-28 w-full" />
					))}
				</div>
			) : (
				<dl
					className={cn(
						CARD_SURFACE,
						"grid min-w-0 grid-cols-1 min-[400px]:grid-cols-2 gap-x-4 gap-y-5 p-4 sm:grid-cols-3 xl:grid-cols-5",
					)}
				>
					{metrics.map((metric) => (
						<div
							key={metric.label}
							className="min-w-0 [overflow-wrap:anywhere]"
						>
							<dt className="text-xs font-medium text-muted-foreground">
								{metric.label}
							</dt>
							<dd
								className={cn(
									"mt-1 text-xl font-semibold tracking-tight tabular-nums",
									metric.alert && "text-[var(--bf-warning)]",
								)}
							>
								{metric.value}
							</dd>
							<dd className="mt-1 text-xs text-muted-foreground">
								{metric.detail}
							</dd>
						</div>
					))}
				</dl>
			)}
		</section>
	);
}
