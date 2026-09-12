import { Button } from "@/components/ui/button";

export function IntegrationReadError({
	resource,
	cached,
	pending,
	onRetry,
}: {
	resource: "integration" | "organizations" | "data providers";
	cached: boolean;
	pending: boolean;
	onRetry: () => void;
}) {
	return (
		<div
			role="alert"
			className="flex flex-col items-start gap-3 rounded-[var(--bf-radius-control)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] p-4 text-sm sm:flex-row sm:items-center sm:justify-between"
		>
			<p>
				Unable to load {resource}.
				{cached
					? " Previously loaded data is still shown."
					: " Retry to continue."}
			</p>
			<Button
				type="button"
				variant="outline"
				className="min-h-11 shrink-0"
				disabled={pending}
				onClick={onRetry}
			>
				{pending ? "Retrying…" : `Retry ${resource}`}
			</Button>
		</div>
	);
}
