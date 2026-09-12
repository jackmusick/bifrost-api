import { Checkbox } from "@/components/ui/checkbox";
import type { ConsumerTabItem } from "./ConsumerTab";

export function ConsumerCards({
	items,
	selected,
	label,
	allSelected,
	someSelected,
	pending,
	hideSecondary,
	showOrg,
	onToggle,
	onToggleAll,
	onItemClick,
	getItemHref,
}: {
	items: ConsumerTabItem[];
	selected: Set<string>;
	label: string;
	allSelected: boolean;
	someSelected: boolean;
	pending: boolean;
	hideSecondary: boolean;
	showOrg: boolean;
	onToggle: (id: string) => void;
	onToggleAll: () => void;
	onItemClick?: (item: ConsumerTabItem) => void;
	getItemHref?: (item: ConsumerTabItem) => string;
}) {
	return (
		<div className="min-w-0 space-y-3">
			<label className="flex min-h-11 items-center gap-3 text-sm">
				<Checkbox
					checked={
						allSelected
							? true
							: someSelected
								? "indeterminate"
								: false
					}
					disabled={pending}
					onCheckedChange={onToggleAll}
					aria-label={`Select all visible ${label}`}
				/>
				Select all visible {label}
			</label>
			<ul aria-label={`Assigned ${label}`} className="space-y-3">
				{items.map((item) => (
					<li
						key={item.id}
						className="min-w-0 rounded-[var(--bf-radius-surface)] border bg-card p-4 [overflow-wrap:anywhere]"
					>
						<label className="flex min-h-11 items-center gap-3 text-sm">
							<Checkbox
								checked={selected.has(item.id)}
								disabled={pending}
								onCheckedChange={() => onToggle(item.id)}
								aria-label={`Select ${item.primary}`}
							/>
							<span className="min-w-0 flex-1 font-medium">
								{item.primary}
							</span>
						</label>
						{showOrg && (
							<p className="mt-2 text-xs text-muted-foreground">
								Organization: {item.org?.name ?? "Platform"}
							</p>
						)}
						{!hideSecondary && item.secondary && (
							<p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
								{item.secondary}
							</p>
						)}
						{getItemHref ? (
							<a
								href={getItemHref(item)}
								className="mt-2 inline-flex min-h-11 items-center text-sm font-medium text-primary"
								onClick={(event) => {
									if (
										onItemClick &&
										!event.ctrlKey &&
										!event.metaKey &&
										!event.shiftKey &&
										!event.altKey
									) {
										event.preventDefault();
										onItemClick(item);
									}
								}}
							>
								Open {item.primary}
							</a>
						) : onItemClick ? (
							<button
								type="button"
								className="mt-2 min-h-11 text-left text-sm font-medium text-primary"
								onClick={() => onItemClick(item)}
							>
								Open {item.primary}
							</button>
						) : null}
					</li>
				))}
			</ul>
		</div>
	);
}
