import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FlaggedRunCard } from "@/components/agents/FlaggedRunCard";
import { FleetReadError } from "./FleetReadError";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/v1";

type AgentRun = components["schemas"]["AgentRunResponse"];
export function TuningFlaggedRuns({
	runs,
	total,
	loading,
	error,
	cached,
	fetching,
	onRetry,
	hasMore,
	loadingMore,
	moreError,
	onLoadMore,
}: {
	runs: AgentRun[];
	total: number;
	loading: boolean;
	error: boolean;
	cached: boolean;
	fetching: boolean;
	onRetry: () => void;
	hasMore: boolean;
	loadingMore: boolean;
	moreError: boolean;
	onLoadMore: () => void;
}) {
	const [open, setOpen] = useState(false);
	const id = useId();
	return (
		<>
			<Button
				type="button"
				variant="outline"
				className="min-h-11 justify-between lg:hidden"
				aria-expanded={open}
				aria-controls={id}
				onClick={() => setOpen(!open)}
			>
				{open ? "Hide" : "Show"} flagged runs ({total})
				<ChevronDown
					aria-hidden="true"
					className={cn(
						"size-4 transition-transform motion-reduce:transition-none",
						open && "rotate-180",
					)}
				/>
			</Button>
			<div className="hidden text-xs font-semibold uppercase tracking-wide text-muted-foreground lg:block">
				Flagged runs ({total})
			</div>
			{error ? (
				<FleetReadError
					resource="flagged runs"
					cached={cached}
					pending={fetching}
					onRetry={onRetry}
				/>
			) : null}
			<div
				id={id}
				className={cn("space-y-3", !open && "hidden lg:block")}
			>
				{error && !cached ? null : loading ? (
					<Skeleton className="h-24 w-full" />
				) : !runs.length ? (
					<p className="rounded-[var(--bf-radius-surface)] border border-dashed p-4 text-center text-sm text-muted-foreground">
						No flagged runs. Mark a run thumbs-down from the runs
						tab to tune against it.
					</p>
				) : (
					<div className="flex flex-col gap-2 lg:max-h-[60vh] lg:overflow-y-auto">
						{runs.map((run) => (
							<FlaggedRunCard key={run.id} run={run} />
						))}
					</div>
				)}
				{hasMore ? (
					<div className="space-y-2">
						{moreError ? (
							<p
								role="alert"
								className="text-sm text-[var(--bf-danger)]"
							>
								Could not load more runs. Loaded runs are still
								available.
							</p>
						) : null}
						<Button
							type="button"
							variant="outline"
							disabled={fetching}
							onClick={onLoadMore}
						>
							{loadingMore
								? "Loading more runs…"
								: moreError
									? "Retry loading more runs"
									: "Load more flagged runs"}
						</Button>
						<p className="text-xs text-muted-foreground">
							{runs.length} of {total} loaded
						</p>
					</div>
				) : null}
			</div>
		</>
	);
}
