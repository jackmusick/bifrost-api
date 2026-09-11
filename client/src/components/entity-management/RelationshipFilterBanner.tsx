import { Network, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RelationshipFilterBannerProps {
	entityName: string;
	isError: boolean;
	isFetching: boolean;
	hasData: boolean;
	onRetry: () => void;
	onClear: () => void;
}

export function RelationshipFilterBanner({
	entityName,
	isError,
	isFetching,
	hasData,
	onRetry,
	onClear,
}: RelationshipFilterBannerProps) {
	const toneClass = isError
		? "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
		: "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)]";

	return (
		<section
			aria-label="Relationship filter"
			className={cn(
				"mb-3 shrink-0 rounded-[var(--bf-radius-surface)] border px-3 py-2",
				toneClass,
			)}
		>
			<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<div className="flex min-w-0 items-center gap-2">
					<Network aria-hidden="true" className="size-4 shrink-0" />
					<p className="min-w-0 text-sm [overflow-wrap:anywhere]">
						All resources <span className="px-1 text-muted-foreground">/</span>{" "}
						<strong className="font-medium text-foreground">
							{entityName}
						</strong>
					</p>
				</div>

				<div className="flex flex-wrap gap-2">
					<Button
						type="button"
						variant="ghost"
						size="sm"
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
