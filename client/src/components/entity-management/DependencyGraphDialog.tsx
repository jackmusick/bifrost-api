import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Network } from "lucide-react";
import { DependencyGraphSurface } from "@/components/dependencies/DependencyGraphSurface";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { DEPENDENCY_GRAPH_LEGEND } from "@/components/dependencies/DependencyGraph";
import type { GraphNode, GraphEdge } from "@/hooks/useDependencyGraph";
import type { EntityType } from "./types";

export interface DependencyGraphDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	entityName: string;
	entityType: EntityType | null;
	graphData: {
		nodes?: GraphNode[];
		edges?: GraphEdge[];
		root_id: string;
	} | null;
	isLoading: boolean;
	isError?: boolean;
	isFetching?: boolean;
	onRetry?: () => void;
}

export function DependencyGraphDialog({
	open,
	onOpenChange,
	entityName,
	entityType,
	graphData,
	isLoading,
	isError = false,
	isFetching = false,
	onRetry,
}: DependencyGraphDialogProps) {
	const focusProps = useDialogReturnFocus();
	const renderLegendItems = () => (
		<div className="grid gap-1.5">
			{DEPENDENCY_GRAPH_LEGEND.map((item) => (
				<div
					key={item.entityType}
					className="flex items-center gap-2 rounded-md px-1 py-1"
				>
					<span
						className="h-3 w-3 shrink-0 rounded-full"
						style={{
							backgroundColor: item.color,
							boxShadow: `0 0 0 1px ${item.softColor}`,
						}}
						aria-hidden="true"
					/>
					<span className="text-sm text-foreground">
						{item.label}
					</span>
				</div>
			))}
		</div>
	);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent
				{...focusProps}
				className="flex h-[calc(100dvh-1rem)] w-[calc(100vw-1rem)] max-w-none flex-col gap-4 overflow-hidden p-4 sm:max-w-none sm:h-[min(88vh,52rem)] sm:w-[min(92vw,72rem)] sm:p-6"
			>
				<DialogHeader className="shrink-0">
					<DialogTitle className="flex max-w-full flex-wrap items-center gap-2 pr-8 leading-tight">
						<Network className="h-5 w-5" />
						<span className="min-w-0 [overflow-wrap:anywhere]">
							Dependency Graph:
						</span>
						<span className="min-w-0 [overflow-wrap:anywhere]">
							{entityName}
						</span>
						{entityType === "app" && (
							<span className="text-xs font-normal text-muted-foreground">
								(All Versions)
							</span>
						)}
					</DialogTitle>
				</DialogHeader>
				<div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_auto] gap-4 lg:grid-cols-[minmax(0,1fr)_18rem] lg:grid-rows-1">
					<DependencyGraphSurface
						graphData={graphData}
						isLoading={isLoading}
						isError={isError}
						isFetching={isFetching}
						onRetry={onRetry}
					/>
					<aside className="min-h-0 overflow-hidden lg:flex lg:flex-col">
						<div className="hidden rounded-lg border border-border/60 bg-background/80 p-3 lg:block lg:max-h-full lg:overflow-y-auto">
							<div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
								Legend
							</div>
							{renderLegendItems()}
						</div>
						<details className="rounded-lg border border-border/60 bg-background/80 p-3 lg:hidden">
							<summary className="-m-3 flex min-h-11 cursor-pointer list-none items-center p-3 text-xs font-medium uppercase tracking-wide text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
								Legend
							</summary>
							<div className="mt-3 max-h-[28vh] overflow-y-auto pr-1">
								{renderLegendItems()}
							</div>
						</details>
					</aside>
				</div>
			</DialogContent>
		</Dialog>
	);
}
