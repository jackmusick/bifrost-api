/**
 * Strip of stat cards for the FleetPage.
 *
 * Inputs come from the FleetStatsResponse hook (T27). The total runs card can
 * optionally render a sparkline if the caller provides a daily breakdown
 * (the OpenAPI FleetStatsResponse does not include one today, so this is
 * a future extension point that doesn't add another API call).
 */

import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatCost, formatNumber } from "@/lib/utils";
import type { components } from "@/lib/v1";

import { Sparkline } from "./Sparkline";

type FleetStatsResponse = components["schemas"]["FleetStatsResponse"];

export interface FleetStatsProps {
	stats: FleetStatsResponse;
	/** Optional per-day run counts for a sparkline on the runs card. */
	runsByDay?: number[];
	/** Optional click handler on the needs-review card. */
	onNeedsReviewClick?: () => void;
	className?: string;
}

export function FleetStats({
	stats,
	runsByDay,
	onNeedsReviewClick,
	className,
}: FleetStatsProps) {
	const successRate = stats.avg_success_rate;
	const successPct = Math.round((successRate ?? 0) * 100);
	const successTone = resolveSuccessTone(successRate);
	const needsReviewTone =
		stats.needs_review > 0 ? "warning" : "success";
	const trendMessage = resolveTrendMessage(runsByDay);
	const hasTrend = trendMessage == null;

	return (
		<dl
			className={cn(
				"grid min-w-0 grid-cols-2 gap-3 [&>div:first-child]:col-span-2 xl:grid-cols-5 xl:[&>div:first-child]:col-span-1",
				className,
			)}
			data-slot="fleet-stats"
		>
			<MetricCard
				label="Runs (7d)"
				value={formatNumber(stats.total_runs)}
				emptyNote={trendMessage ?? undefined}
				sparkline={
					hasTrend && runsByDay != null ? (
						<Sparkline
							values={runsByDay}
							colorClass="text-[var(--bf-info)]"
							ariaLabel="Runs trend over the last 7 days"
						/>
					) : null
				}
			/>
			<MetricCard
				label="Avg success rate"
				value={`${successPct}%`}
				valueTone={successTone}
			/>
			<MetricCard
				label="Spend (7d)"
				value={formatCost(stats.total_cost_7d)}
			/>
			<MetricCard
				label="Active agents"
				value={formatNumber(stats.active_agents)}
			/>
			<MetricCard
				label="Needs review"
				value={formatNumber(stats.needs_review)}
				valueTone={needsReviewTone}
				icon={
					stats.needs_review > 0 ? (
						<AlertTriangle size={11} />
					) : undefined
				}
				onClick={
					stats.needs_review > 0 ? onNeedsReviewClick : undefined
				}
			/>
		</dl>
	);
}

interface MetricCardProps {
	label: string;
	value: string;
	icon?: React.ReactNode;
	valueTone?: "neutral" | "info" | "success" | "warning" | "danger";
	emptyNote?: string;
	sparkline?: React.ReactNode;
	onClick?: () => void;
}

function MetricCard({
	label,
	value,
	icon,
	valueTone = "neutral",
	emptyNote,
	sparkline,
	onClick,
}: MetricCardProps) {
	const interactive = typeof onClick === "function";

	return (
		<div
			role={interactive ? "button" : undefined}
			tabIndex={interactive ? 0 : undefined}
			onClick={onClick}
			onKeyDown={(e) => {
				if (interactive && (e.key === "Enter" || e.key === " ")) {
					e.preventDefault();
					onClick?.();
				}
			}}
			className={cn(
				"min-w-0 rounded-[var(--bf-radius-surface)] border border-border bg-card p-3 transition-colors motion-reduce:transition-none sm:p-4",
				interactive && "cursor-pointer hover:bg-accent/40",
				interactive &&
					"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
			)}
			data-slot="stat-card"
			data-tone={valueTone}
		>
			<dt
				className="flex min-h-8 items-center gap-1.5 text-xs font-medium leading-4 text-muted-foreground"
			>
				{icon}
				{label}
			</dt>
			<dd
				className={cn(
					"mt-1 text-base font-semibold leading-tight tracking-tight tabular-nums [overflow-wrap:anywhere] sm:text-xl",
					toneClass(valueTone),
				)}
			>
				{value}
			</dd>
			{emptyNote ? (
				<dd
					className={cn(
						"mt-1 text-xs leading-5 text-muted-foreground",
					)}
				>
					{emptyNote}
				</dd>
			) : null}
			{sparkline ? (
				<div className="mt-3 h-10">{sparkline}</div>
			) : null}
		</div>
	);
}

function resolveSuccessTone(
	rate: number | null | undefined,
): "neutral" | "info" | "success" | "warning" | "danger" {
	if (rate == null) return "neutral";
	if (rate >= 0.9) return "success";
	if (rate >= 0.75) return "warning";
	return "danger";
}

function resolveTrendMessage(runsByDay?: number[]) {
	if (!runsByDay || runsByDay.length < 2) return "No daily trend yet";
	return runsByDay.some((value) => value > 0) ? null : "No activity yet";
}

function toneClass(tone: "neutral" | "info" | "success" | "warning" | "danger") {
	switch (tone) {
		case "info":
			return "text-[var(--bf-info)]";
		case "success":
			return "text-[var(--bf-success)]";
		case "warning":
			return "text-[var(--bf-warning)]";
		case "danger":
			return "text-[var(--bf-danger)]";
		case "neutral":
		default:
			return "text-foreground";
	}
}

/** Re-export formatCost so consumers can format the cost string from the API. */
export { formatCost };
