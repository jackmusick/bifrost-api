import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EntityCollectionState {
	name: string;
	isLoading: boolean;
	isFetching: boolean;
	isError: boolean;
	hasData: boolean;
	onRetry: () => void;
}

/** Keep unavailable collections distinct from confirmed empty collections. */
export function EntityCollectionStatus({
	collections,
}: {
	collections: EntityCollectionState[];
}) {
	const visible = collections.filter(
		(collection) => collection.isError || collection.isFetching || collection.isLoading,
	);
	if (!visible.length) return null;

	return (
		<section
			aria-label="Entity data status"
			className="shrink-0 space-y-3"
		>
			{visible.map((collection) => {
				const isRetrying = collection.isError && collection.isFetching;
				const isRefreshing = !collection.isError && collection.isFetching;
				const isLoading = collection.isLoading && !collection.hasData;
				const toneClass = collection.isError
					? "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
					: "border-border bg-muted/20 text-foreground";

				return (
					<div
						key={collection.name}
						className={cn(
							"flex flex-col gap-3 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)] sm:flex-row sm:items-center sm:justify-between",
							toneClass,
						)}
					>
						<div className="flex min-w-0 items-start gap-3">
							<div
								className={cn(
									"mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)]",
									collection.isError
										? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
										: isRefreshing
											? "bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
											: "bg-background text-muted-foreground",
								)}
							>
								{collection.isError ? (
									<AlertTriangle aria-hidden="true" className="size-4" />
								) : isLoading ? (
									<Loader2
										aria-hidden="true"
										className="size-4 animate-spin motion-reduce:animate-none"
									/>
								) : (
									<RefreshCw
										aria-hidden="true"
										className="size-4 animate-spin motion-reduce:animate-none"
									/>
								)}
							</div>
							<div className="min-w-0 space-y-1">
								<p className="text-sm font-medium [overflow-wrap:anywhere]">
									{collection.name}
								</p>
								{collection.isError ? (
									<p
										role="alert"
										className="text-sm [overflow-wrap:anywhere]"
									>
										<span className="font-medium">
											{collection.name} could not be loaded.
										</span>{" "}
										{collection.hasData
											? "Showing the last available data."
											: "This part of the page is incomplete."}
									</p>
								) : (
									<p
										role="status"
										className="text-sm text-muted-foreground"
									>
										{isLoading
											? `Loading ${collection.name.toLowerCase()}…`
											: `Refreshing ${collection.name.toLowerCase()}…`}
									</p>
								)}
							</div>
						</div>

						{collection.isError ? (
							<Button
								type="button"
								variant="outline"
								size="lg"
								className="w-full sm:w-auto"
								disabled={collection.isFetching}
								onClick={collection.onRetry}
								aria-label={`Retry ${collection.name.toLowerCase()}`}
							>
								{isRetrying ? "Retrying…" : "Retry"}
							</Button>
						) : null}
					</div>
				);
			})}
		</section>
	);
}
