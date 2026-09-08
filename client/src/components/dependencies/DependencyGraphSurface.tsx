import { AlertTriangle, Network } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DependencyGraph } from "./DependencyGraph";
import type { GraphNode, GraphEdge } from "@/hooks/useDependencyGraph";

export interface DependencyGraphSurfaceProps {
	graphData: {
		nodes?: GraphNode[];
		edges?: GraphEdge[];
		root_id: string;
	} | null;
	isLoading: boolean;
	isError?: boolean;
	isFetching?: boolean;
	onRetry?: (() => void) | undefined;
}

export function DependencyGraphSurface({
	graphData,
	isLoading,
	isError = false,
	isFetching = false,
	onRetry,
}: DependencyGraphSurfaceProps) {
	const hasGraph = !!graphData?.nodes?.length && !!graphData.edges;
	return (
		<section
			aria-label="Dependency graph"
			aria-busy={isLoading || isFetching}
			className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border bg-background"
		>
			{isError && (
				<div className="shrink-0 border-b border-[color:var(--bf-danger-soft)] bg-[color:var(--bf-danger-soft)]/35 p-3">
					<div className="flex items-start gap-3">
						<span
							className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-background text-[var(--bf-danger)]"
							aria-hidden="true"
						>
							<AlertTriangle className="size-4" />
						</span>
						<div className="min-w-0 space-y-2">
							<p role="alert" className="text-sm font-medium text-[var(--bf-danger)]">
								Couldn’t load dependencies.
								{hasGraph ? " The previously loaded graph is shown." : ""}
							</p>
						</div>
					</div>
					{onRetry && (
						<Button
							type="button"
							variant="outline"
							className="mt-3 min-h-11"
							disabled={isFetching}
							onClick={onRetry}
						>
							{isFetching ? "Retrying…" : "Retry dependencies"}
						</Button>
					)}
				</div>
			)}
			{hasGraph && (isLoading || isFetching) && (
				<p
					role="status"
					className="shrink-0 border-b border-[color:var(--bf-info-soft)] bg-[color:var(--bf-info-soft)]/25 px-3 py-2 text-sm text-foreground"
				>
					Refreshing dependencies…
				</p>
			)}
			{hasGraph ? (
				<div className="min-h-0 min-w-0 flex-1">
					<DependencyGraph
						nodes={graphData!.nodes!}
						edges={graphData!.edges!}
						rootId={graphData!.root_id}
						className="h-full"
					/>
				</div>
			) : isLoading || isFetching ? (
				<div
					role="status"
					className="m-auto w-full max-w-sm space-y-4 rounded-[var(--bf-radius-surface)] border border-[color:var(--bf-info-soft)] bg-[color:var(--bf-info-soft)]/20 p-4"
				>
					<Skeleton className="h-20 w-full rounded-[var(--bf-radius-surface)]" />
					<p className="text-center text-sm text-muted-foreground">
						Loading dependency graph…
					</p>
				</div>
			) : !isError ? (
				<div className="m-auto w-full max-w-sm space-y-3 rounded-[var(--bf-radius-surface)] border border-dashed border-[color:var(--bf-info-soft)] bg-[color:var(--bf-info-soft)]/15 p-4 text-center">
					<Network className="mx-auto size-8 text-[var(--bf-info)]" />
					<h3 className="text-sm font-medium">
						{graphData
							? "No dependencies found"
							: "No dependency graph available"}
					</h3>
					<p className="text-sm text-muted-foreground">
						{graphData
							? "This entity has no dependencies to visualize."
							: "Select an entity to view its dependencies."}
					</p>
				</div>
			) : null}
		</section>
	);
}
