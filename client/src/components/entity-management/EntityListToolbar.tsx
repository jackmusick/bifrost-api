import { useId, useRef, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

import type { SortOption } from "./types";

interface EntityListToolbarProps {
	search: string;
	onSearch: (value: string) => void;
	allSelected: boolean;
	someSelected: boolean;
	onSelectAll: (selected: boolean) => void;
	visibleCount: number;
	selectedCount: number;
	hiddenSelectedCount: number;
	onClearSelection: () => void;
	onDelete: () => void;
	busy: boolean;
	busyMessage: string;
	filters?: ReactNode;
	assignmentAction?: ReactNode;
	sortBy: SortOption;
	onSortBy: (value: SortOption) => void;
	ascending: boolean;
	onToggleDirection: () => void;
}

export function EntityListToolbar({
	search,
	onSearch,
	allSelected,
	someSelected,
	onSelectAll,
	visibleCount,
	selectedCount,
	hiddenSelectedCount,
	onClearSelection,
	onDelete,
	busy,
	busyMessage,
	filters,
	assignmentAction,
	sortBy,
	onSortBy,
	ascending,
	onToggleDirection,
}: EntityListToolbarProps) {
	const input = useRef<HTMLInputElement>(null);
	const sortId = useId();
	const selectAllId = useId();
	const selectionSummary =
		selectedCount > 0
			? `${selectedCount} selected${
					hiddenSelectedCount > 0
						? ` (${hiddenSelectedCount} outside this view)`
						: ""
				}`
			: null;

	return (
		<section
			aria-label="Entity list controls"
			className="mb-4 shrink-0 space-y-3 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]"
		>
			<div className="grid gap-3">
				<div className="flex items-center gap-2">
					<label
						htmlFor={selectAllId}
						className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-[var(--bf-radius-control)] border border-border bg-background"
					>
						<Checkbox
							id={selectAllId}
							aria-label="Select all visible entities"
							checked={
								someSelected ? "indeterminate" : allSelected
							}
							disabled={visibleCount === 0 || busy}
							onCheckedChange={(value) =>
								onSelectAll(value === true)
							}
						/>
					</label>
					<div className="relative min-w-0 flex-1">
						<Input
							ref={input}
							aria-label="Search entities"
							placeholder="Search entities…"
							value={search}
							onChange={(event) => onSearch(event.target.value)}
							className="min-h-11 pr-11"
						/>
						{search ? (
							<Button
								type="button"
								variant="ghost"
								size="icon-sm"
								className="absolute right-0 top-0 size-11"
								aria-label="Clear search"
								onClick={() => {
									onSearch("");
									input.current?.focus();
								}}
							>
								<X aria-hidden="true" className="size-4" />
							</Button>
						) : null}
					</div>
				</div>

				<div className="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
					<div className="col-span-2 flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:col-span-1">
						{filters}
					</div>
					<label htmlFor={sortId} className="sr-only">
						Sort by
					</label>
					<select
						id={sortId}
						value={sortBy}
						onChange={(event) =>
							onSortBy(event.target.value as SortOption)
						}
						className="min-h-11 min-w-0 rounded-[var(--bf-radius-control)] border border-border bg-background px-3 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-ring"
					>
						<option value="name">Name</option>
						<option value="date">Date</option>
						<option value="type">Type</option>
					</select>
					<Button
						type="button"
						variant="outline"
						size="icon-lg"
						className="shrink-0 justify-self-start sm:justify-self-auto"
						aria-label={
							ascending ? "Sort descending" : "Sort ascending"
						}
						title={
							ascending
								? "Ascending; switch to descending"
								: "Descending; switch to ascending"
						}
						onClick={onToggleDirection}
					>
						{ascending ? (
							<ArrowUp aria-hidden="true" className="size-4" />
						) : (
							<ArrowDown aria-hidden="true" className="size-4" />
						)}
					</Button>
				</div>
			</div>

			{selectionSummary || busy ? (
				<div className="flex flex-col gap-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 px-3 py-2 text-sm lg:flex-row lg:items-center lg:justify-between">
					<p
						role="status"
						className="min-w-0 flex-1 basis-full text-muted-foreground"
					>
						{busy ? busyMessage : selectionSummary}
					</p>
					{selectedCount > 0 ? (
						<div className="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-none sm:flex sm:flex-wrap sm:items-center">
							{assignmentAction}
							<Button
								type="button"
								variant="outline"
								size="lg"
								className="w-full sm:w-auto"
								disabled={busy}
								onClick={onClearSelection}
							>
								Clear selection
							</Button>
							<Button
								type="button"
								variant="outline"
								size="lg"
								className="w-full text-destructive sm:w-auto"
								disabled={busy}
								onClick={onDelete}
							>
								<Trash2 aria-hidden="true" className="size-4" />
								Delete selected
							</Button>
						</div>
					) : null}
				</div>
			) : null}
		</section>
	);
}
