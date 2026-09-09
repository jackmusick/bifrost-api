import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface EntityCollectionState {
	name: string;
	isLoading: boolean;
	isFetching: boolean;
	isError: boolean;
	hasData: boolean;
	onRetry: () => void;
}

/** Surface partial failures without adding competing loading rows above the workspace. */
export function EntityCollectionStatus({
	collections,
}: {
	collections: EntityCollectionState[];
}) {
	const failed = collections.filter((collection) => collection.isError);
	if (!failed.length) return null;
	return (
		<section aria-label="Entity data status" className="shrink-0 space-y-3">
			{failed.map((collection) => (
				<div
					key={collection.name}
					className="flex flex-col gap-3 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] p-[var(--bf-surface-pad)] text-[var(--bf-danger)] sm:flex-row sm:items-center sm:justify-between"
				>
					<div className="flex min-w-0 items-start gap-3">
						<AlertTriangle
							aria-hidden="true"
							className="mt-0.5 size-5 shrink-0"
						/>
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
					</div>
					<Button
						type="button"
						variant="outline"
						size="lg"
						className="w-full sm:w-auto"
						disabled={collection.isFetching}
						onClick={collection.onRetry}
						aria-label={`Retry ${collection.name.toLowerCase()}`}
					>
						{collection.isFetching ? "Retrying…" : "Retry"}
					</Button>
				</div>
			))}
		</section>
	);
}
