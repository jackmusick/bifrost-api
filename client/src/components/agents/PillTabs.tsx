import { cn } from "@/lib/utils";

export interface PillTabItem {
	value: string;
	label: string;
	/** Optional count badge rendered after the label — e.g. "Runs 14". */
	count?: number;
	disabled?: boolean;
}

export interface PillTabsProps {
	items: PillTabItem[];
	value: string;
	onValueChange: (v: string) => void;
	className?: string;
}

/** Agent tab navigation with controlled selection and keyboard navigation. */
export function PillTabs({
	items,
	value,
	onValueChange,
	className,
}: PillTabsProps) {
	const focusValue = items.find((item) => item.value === value && !item.disabled)?.value ?? items.find((item) => !item.disabled)?.value;
	return (
		<div
			role="tablist"
			className={cn(
				"flex max-w-full items-center gap-1 overflow-x-auto border-b border-border",
				className,
			)}
		>
			{items.map((item) => {
				const active = item.value === value;
				return (
					<button
						key={item.value}
						type="button"
						role="tab"
						aria-selected={active}
						tabIndex={item.value === focusValue ? 0 : -1}
						onKeyDown={(event) => {
							if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
							event.preventDefault();
							const enabled = items.filter((tab) => !tab.disabled);
							const index = enabled.findIndex((tab) => tab.value === item.value);
							const next = event.key === "Home" ? 0 : event.key === "End" ? enabled.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + enabled.length) % enabled.length;
							const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
							buttons?.[next]?.focus();
							onValueChange(enabled[next].value);
						}}
						disabled={item.disabled}
						onClick={() => !item.disabled && onValueChange(item.value)}
						className={cn(
							"inline-flex min-h-11 shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm transition-colors duration-[var(--bf-motion-feedback)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring motion-reduce:transition-none",
							active
								? "border-primary text-primary"
								: "border-transparent text-muted-foreground hover:text-foreground",
							item.disabled && "opacity-40 cursor-not-allowed",
						)}
					>
						{item.label}
						{item.count != null && item.count > 0 ? (
							<span
								className={cn(
									"inline-flex items-center justify-center rounded-full px-1.5 py-px text-[11px] font-medium tabular-nums",
									active
										? "bg-muted text-foreground"
										: "bg-muted/60 text-muted-foreground",
								)}
							>
								{item.count}
							</span>
						) : null}
					</button>
				);
			})}
		</div>
	);
}
