import { Network, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RelationshipFilterBannerProps {
	entityName: string;
	isError: boolean;
	isFetching: boolean;
	hasData: boolean;
	onRetry: () => void;
	onViewGraph: () => void;
	onClear: () => void;
}

export function RelationshipFilterBanner({
	entityName,
	isError,
	isFetching,
	hasData,
	onRetry,
	onViewGraph,
	onClear,
}: RelationshipFilterBannerProps) {
	const toneClass = isError
		? "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
		: "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)]";

	return (
		<section
			aria-label="Relationship filter"
			className={cn(
				"mb-4 space-y-4 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)]",
				toneClass,
			)}
		>
			<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div className="flex min-w-0 items-start gap-3">
					<div
						className={cn(
							"mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)]",
							isError
								? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
								: "bg-background text-[var(--bf-info)]",
						)}
					>
						<Network aria-hidden="true" className="size-4" />
					</div>
					<div className="min-w-0 space-y-1">
						<p className="text-sm font-medium leading-6 [overflow-wrap:anywhere]">
							Related to{" "}
							<strong className="text-foreground">{entityName}</strong>
						</p>
						<p className="text-sm text-muted-foreground">
							View relationships in the graph or clear the filter to return to
							the full list.
						</p>
					</div>
				</div>

				<div className="flex flex-wrap gap-2">
					<Button
						type="button"
						variant="outline"
						size="lg"
						className="w-full sm:w-auto"
						onClick={onViewGraph}
					>
						View graph
					</Button>
					<Button
						type="button"
						variant="ghost"
						size="lg"
						className="w-full sm:w-auto"
						onClick={onClear}
					>
						<X aria-hidden="true" className="size-4" />
						Clear filter
					</Button>
				</div>
			</div>

			{isError ? (
				<div
					role="alert"
					className="space-y-3 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] px-4 py-3 text-sm text-[var(--bf-danger)]"
				>
					<p className="[overflow-wrap:anywhere]">
						{hasData
							? "Could not refresh relationships. Showing the last available results."
							: "Could not load relationships. Retry to see related entities."}
					</p>
					<Button
						type="button"
						variant="outline"
						size="lg"
						className="w-full sm:w-auto"
						disabled={isFetching}
						onClick={onRetry}
					>
						{isFetching ? "Retrying…" : "Retry relationships"}
					</Button>
				</div>
			) : isFetching ? (
				<p role="status" className="text-sm text-muted-foreground">
					{hasData ? "Refreshing relationships…" : "Loading relationships…"}
				</p>
			) : null}
			{isError && isFetching ? (
				<p role="status" className="text-sm text-muted-foreground">
					Retrying relationships…
				</p>
			) : null}
		</section>
	);
}
