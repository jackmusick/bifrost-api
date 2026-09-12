import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { TYPE_MONO } from "./design-tokens";

export type ChipTone = "muted" | "primary" | "emerald" | "rose" | "yellow";

export interface ChipProps {
	children: ReactNode;
	/** Label shown before the value, e.g. `ticket_id` in `ticket_id 4822`. */
	label?: string;
	tone?: ChipTone;
	mono?: boolean;
	className?: string;
}

const TONE_CLASSES: Record<ChipTone, string> = {
	muted: "bg-muted/60 text-muted-foreground border-border",
	primary: "bg-primary/15 text-primary border-transparent",
	emerald:
		"bg-[var(--bf-success-soft)] text-[var(--bf-success)] border-transparent",
	rose: "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)] border-transparent",
	yellow: "bg-[var(--bf-warning-soft)] text-[var(--bf-warning)] border-transparent",
};

/**
 * Consistent metadata tag for captured metadata (`ticket_id 4822`, `customer Globex`).
 * Supports an optional muted `label` prefix rendered at lower
 * weight. Mono treatment for IDs/hashes.
 */
export function Chip({
	children,
	label,
	tone = "muted",
	mono,
	className,
}: ChipProps) {
	return (
		<span
			className={cn(
				"inline-flex max-w-full min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 rounded-[var(--bf-radius-control)] border px-2 py-1 text-sm font-medium",
				TONE_CLASSES[tone],
				className,
			)}
		>
			{label ? (
				<span className="text-muted-foreground [overflow-wrap:anywhere]">
					{label}
				</span>
			) : null}
			<span
				className={cn(
					mono && TYPE_MONO,
					"min-w-0 text-sm [overflow-wrap:anywhere]",
				)}
			>
				{children}
			</span>
		</span>
	);
}
