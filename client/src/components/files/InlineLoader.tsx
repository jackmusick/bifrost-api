import { Loader2 } from "lucide-react";

/**
 * Small inline spinner + label for the explorer's loading states, so they read
 * as "working" rather than a static line of text.
 */
export function InlineLoader({
	label = "Loading…",
	className = "",
}: {
	label?: string;
	className?: string;
}) {
	return (
		<div
			role="status"
			className={`flex items-center gap-2 text-sm text-muted-foreground ${className}`}
		>
			<Loader2 aria-hidden="true" className="h-4 w-4 animate-spin motion-reduce:animate-none" />
			<span>{label}</span>
		</div>
	);
}
