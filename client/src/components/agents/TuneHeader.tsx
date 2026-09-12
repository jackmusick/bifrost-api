import type { ReactNode } from "react";
import { ArrowLeft, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatNumber, formatRelativeTime } from "@/lib/utils";
import type { components } from "@/lib/v1";

import { GAP_CARD, TONE_MUTED, TYPE_BODY } from "./design-tokens";
import { StatCard } from "./StatCard";

type AgentStats = components["schemas"]["AgentStatsResponse"];

export interface TuneHeaderProps {
	agentId: string | undefined;
	agentName: string | undefined;
	flaggedCount: number;
	stats: AgentStats | null;
	statsLoading: boolean;
	/** Action slot rendered at the top-right of the header. */
	action?: ReactNode;
}

export function TuneHeader({
	agentId,
	agentName,
	flaggedCount,
	stats,
	statsLoading,
	action,
}: TuneHeaderProps) {
	return (
		<div className="flex flex-col gap-4">
			<div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
				<Link
					to={agentId ? `/agents/${agentId}` : "/agents"}
					className="inline-flex min-h-11 min-w-0 items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground [overflow-wrap:anywhere]"
				>
					<ArrowLeft className="size-4 shrink-0" />
					{agentName ?? "Back to agent"}
				</Link>
				<span aria-hidden="true" className="hidden text-xs text-muted-foreground sm:inline">·</span>
				<Link
					to={agentId ? `/agents/${agentId}/review` : "/agents"}
					className="inline-flex min-h-11 items-center text-sm text-muted-foreground hover:text-foreground"
				>
					Review flagged runs
				</Link>
			</div>

			<div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
				<div className="min-w-0">
					<h1 className="flex items-center gap-2 font-display text-2xl font-semibold tracking-tight sm:text-3xl">
						<Sparkles
							className="size-6 shrink-0 text-primary"
							aria-hidden="true"
						/>
						Tune agent
					</h1>
					<p
						className={cn(
							"mt-2 [overflow-wrap:anywhere]",
							TYPE_BODY,
							TONE_MUTED,
						)}
					>
						Refine {agentName ?? "this agent"}
						&apos;s prompt against {flaggedCount} flagged run
						{flaggedCount === 1 ? "" : "s"}. Use a dry-run to
						evaluate your proposal before applying it.
					</p>
				</div>
				{action ? (
					<div className="flex shrink-0 items-center gap-2 [&>button]:min-h-11 [&>button]:flex-1">
						{action}
					</div>
				) : null}
			</div>

			<div className={cn("grid grid-cols-2 lg:grid-cols-4", GAP_CARD)}>
				{statsLoading ? (
					<>
						{[0, 1, 2, 3].map((i) => (
							<Skeleton
								key={i}
								data-testid="stat-skeleton"
								className="h-24 w-full"
							/>
						))}
					</>
				) : stats ? (
					<>
						<StatCard
							label="Flagged runs"
							value={formatNumber(flaggedCount)}
							alert={flaggedCount > 0}
						/>
						<StatCard
							label="Runs (7d)"
							value={formatNumber(stats.runs_7d)}
						/>
						<StatCard
							label="Success rate"
							value={`${Math.round(
								(stats.success_rate ?? 0) * 100,
							)}%`}
						/>
						<StatCard
							label="Last run"
							value={
								stats.last_run_at
									? formatRelativeTime(stats.last_run_at)
									: "—"
							}
						/>
					</>
				) : null}
			</div>
		</div>
	);
}
