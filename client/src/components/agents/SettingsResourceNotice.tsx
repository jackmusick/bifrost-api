import { Button } from "@/components/ui/button";

export function SettingsResourceNotice({
	resource,
	failed,
	loading,
	cached,
	pending,
	onRetry,
}: {
	resource: string;
	failed: boolean;
	loading: boolean;
	cached: boolean;
	pending: boolean;
	onRetry: () => void;
}) {
	if (loading)
		return (
			<p role="status" className="sr-only">
				Loading {resource}…
			</p>
		);
	if (!failed) return null;
	return (
		<div
			role="alert"
			className="space-y-3 rounded-[var(--bf-radius-surface)] border bg-[var(--bf-warning-soft)] p-4 text-sm"
		>
			<p>
				Could not {cached ? "refresh" : "load"} {resource}.{" "}
				{cached
					? "Previously loaded options are still available."
					: "Your saved selections have not changed."}
			</p>
			<Button
				type="button"
				variant="outline"
				className="h-auto min-h-11 max-w-full whitespace-normal text-left [overflow-wrap:anywhere]"
				disabled={pending}
				onClick={onRetry}
			>
				Retry {resource}
			</Button>
		</div>
	);
}
