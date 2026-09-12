import { Button } from "@/components/ui/button";

export function MessageHistoryError({ cached, pending, onRetry }: {
	cached: boolean;
	pending: boolean;
	onRetry: () => void;
}) {
	return (
		<div role="alert" className="m-4 flex flex-col items-start gap-3 rounded-[var(--bf-radius-control)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
			<p>{cached ? "Could not refresh message history. Messages already loaded are still shown." : "Message history could not be loaded. Retry to continue this conversation."}</p>
			<Button type="button" variant="outline" className="min-h-11 shrink-0" disabled={pending} onClick={onRetry}>{pending ? "Retrying…" : "Retry messages"}</Button>
		</div>
	);
}
