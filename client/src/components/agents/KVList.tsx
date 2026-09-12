import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { TONE_MUTED, TYPE_MONO } from "./design-tokens";

export interface KVItem {
	label: string;
	value: ReactNode;
	/** Render value with mono font (for keys, hashes, model names). */
	mono?: boolean;
}

export interface KVListProps {
	items: KVItem[];
	className?: string;
}

/** Label/value records stack inside narrow panels and retain complete values. */
export function KVList({ items, className }: KVListProps) {
	return (
		<dl className={cn("@container min-w-0 space-y-3 text-sm", className)}>
			{items.map((item, idx) => (
				<div
					key={idx}
					className="grid min-w-0 gap-1 @sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] @sm:gap-x-3"
				>
					<dt
						className={cn(
							TONE_MUTED,
							"min-w-0 [overflow-wrap:anywhere]",
						)}
					>
						{item.label}
					</dt>
					<dd
						className={cn(
							item.mono && TYPE_MONO,
							"m-0 min-w-0 text-sm [overflow-wrap:anywhere]",
						)}
					>
						{item.value}
					</dd>
				</div>
			))}
		</dl>
	);
}
