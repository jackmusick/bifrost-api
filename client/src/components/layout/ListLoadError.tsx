import { Button } from "@/components/ui/button";

interface ListLoadErrorProps {
	resource: string;
	hasCachedData: boolean;
	isRetrying: boolean;
	onRetry: () => void;
}

/** Keep failed reads distinct from empty results without hiding cached records. */
export function ListLoadError({ resource, hasCachedData, isRetrying, onRetry }: ListLoadErrorProps) {
	return (
		<div role="alert" className="flex flex-col items-start gap-3 rounded-[var(--bf-radius-surface)] border border-destructive/30 p-4 sm:flex-row sm:items-center sm:justify-between">
			<p className="text-sm text-destructive">
				Couldn't load {resource}.{hasCachedData && " Previously loaded records are shown below."}
			</p>
			<Button type="button" variant="outline" className="min-h-11 shrink-0" disabled={isRetrying} onClick={onRetry}>
				{isRetrying ? "Retrying…" : "Retry loading"}
			</Button>
		</div>
	);
}
