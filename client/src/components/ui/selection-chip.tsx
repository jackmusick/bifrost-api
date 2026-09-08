import type { MouseEventHandler } from "react";
import { X } from "lucide-react";

/** A removable selected value, shared by multi-select fields. */
export function SelectionChip({
	label,
	disabled = false,
	onRemove,
}: {
	label: string;
	disabled?: boolean;
	onRemove: MouseEventHandler<HTMLButtonElement>;
}) {
	return (
		<span className="inline-flex max-w-full min-w-0 items-center gap-1 rounded-md border border-border/70 bg-muted/60 pl-2 text-xs font-medium leading-5 text-foreground">
			<span className="min-w-0 py-0.5 [overflow-wrap:anywhere]">
				{label}
			</span>
			<button
				type="button"
				disabled={disabled}
				aria-label={`Remove ${label}`}
				onClick={onRemove}
				className="inline-flex size-7 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 motion-reduce:transition-none [@media(pointer:coarse)]:size-9"
			>
				<X className="size-3.5" />
			</button>
		</span>
	);
}
