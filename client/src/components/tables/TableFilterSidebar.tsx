/**
 * Table Filter Sidebar Component
 *
 * Collapsible sidebar for filtering table documents with query conditions.
 * Similar to WorkflowSidebar but tailored for document querying.
 */

import { useState } from "react";
import {
	ChevronDown,
	ChevronRight,
	Plus,
	Trash2,
	X,
	Filter,
	PanelLeftClose,
	Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { QueryOperator } from "@/services/tables";

interface FilterCondition {
	id: string;
	field: string;
	operator: QueryOperator;
	value: string;
}

const OPERATORS: { value: QueryOperator; label: string }[] = [
	{ value: "eq", label: "equals" },
	{ value: "ne", label: "not equals" },
	{ value: "contains", label: "contains" },
	{ value: "starts_with", label: "starts with" },
	{ value: "ends_with", label: "ends with" },
	{ value: "gt", label: ">" },
	{ value: "gte", label: ">=" },
	{ value: "lt", label: "<" },
	{ value: "lte", label: "<=" },
	{ value: "in", label: "in list" },
	{ value: "is_null", label: "is null" },
	{ value: "has_key", label: "has field" },
];

function generateId() {
	return Math.random().toString(36).substring(2, 9);
}

function getBooleanConditionValue(value: string) {
	return value === "false" ? "false" : "true";
}

interface FiltersSectionProps {
	conditions: FilterCondition[];
	onAdd: () => void;
	onRemove: (id: string) => void;
	onUpdate: (id: string, updates: Partial<FilterCondition>) => void;
}

function FiltersSection({
	conditions,
	onAdd,
	onRemove,
	onUpdate,
}: FiltersSectionProps) {
	const [isExpanded, setIsExpanded] = useState(true);

	return (
		<div className="min-w-0">
			<button
				type="button"
				aria-expanded={isExpanded}
				aria-label={
					isExpanded
						? "Collapse query filters"
						: "Expand query filters"
				}
				onClick={() => setIsExpanded(!isExpanded)}
				className="flex min-h-11 w-full items-center justify-between gap-3 border-b border-border/60 px-4 py-3 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
			>
				<div className="flex min-w-0 items-center gap-2">
					{isExpanded ? (
						<ChevronDown className="size-4 text-muted-foreground" />
					) : (
						<ChevronRight className="size-4 text-muted-foreground" />
					)}
					<Filter className="size-4 text-muted-foreground" />
					<span className="truncate font-medium text-sm">
						Query Filters
					</span>
				</div>
				<Badge
					variant="secondary"
					className="min-w-7 justify-center text-xs"
				>
					{conditions.length}
				</Badge>
			</button>

			{isExpanded && (
				<div className="space-y-3 px-4 py-3">
					{conditions.length === 0 ? (
						<div className="py-2 text-sm text-muted-foreground">
							No filters applied
						</div>
					) : (
						<div className="space-y-3">
							{conditions.map((condition, index) => (
								<div
									key={condition.id}
									className="space-y-3 border-b border-border/60 pb-3 last:border-b-0 last:pb-0"
								>
									<div className="flex items-start gap-2">
										<Input
											aria-label={`Filter field ${index + 1}`}
											placeholder="Field name"
											value={condition.field}
											onChange={(e) =>
												onUpdate(condition.id, {
													field: e.target.value,
												})
											}
											className="min-h-11 min-w-0 flex-1"
										/>
										<Button
											type="button"
											variant="ghost"
											size="icon"
											onClick={() =>
												onRemove(condition.id)
											}
											aria-label={`Remove filter ${index + 1}`}
											className="h-11 w-11 shrink-0 text-muted-foreground"
										>
											<Trash2 className="size-4" />
										</Button>
									</div>
									<div className="grid gap-2">
										<Select
											value={condition.operator}
											onValueChange={(
												value: QueryOperator,
											) =>
												onUpdate(condition.id, {
													operator: value,
												})
											}
										>
											<SelectTrigger
												aria-label={`Filter operator ${index + 1}`}
												className="min-h-11 w-full"
											>
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												{OPERATORS.map((op) => (
													<SelectItem
														key={op.value}
														value={op.value}
													>
														{op.label}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
										{condition.operator === "is_null" ||
										condition.operator === "has_key" ? (
											<Select
												value={getBooleanConditionValue(
													condition.value,
												)}
												onValueChange={(value) =>
													onUpdate(condition.id, {
														value,
													})
												}
											>
												<SelectTrigger
													aria-label={`Filter boolean value ${index + 1}`}
													className="min-h-11 w-full"
												>
													<SelectValue />
												</SelectTrigger>
												<SelectContent>
													<SelectItem value="true">
														true
													</SelectItem>
													<SelectItem value="false">
														false
													</SelectItem>
												</SelectContent>
											</Select>
										) : (
											<Input
												aria-label={`Filter value ${index + 1}`}
												placeholder="Value"
												value={condition.value}
												onChange={(e) =>
													onUpdate(condition.id, {
														value: e.target.value,
													})
												}
												className="min-h-11 min-w-0"
											/>
										)}
									</div>
								</div>
							))}
						</div>
					)}
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={onAdd}
						className="min-h-11 w-full"
					>
						<Plus className="size-4" />
						Add Filter
					</Button>
				</div>
			)}
		</div>
	);
}

export interface TableFilterSidebarProps {
	/** Callback to apply filters */
	onApplyFilters: (where: Record<string, unknown>) => void;
	/** Callback to clear all filters */
	onClearFilters: () => void;
	/** Whether there are active filters */
	hasActiveFilters: boolean;
	/** Callback to close/collapse the sidebar */
	onClose?: () => void;
	/** Additional CSS classes */
	className?: string;
}

/**
 * Table Filter Sidebar
 *
 * Provides a sidebar interface for building document query filters.
 */
export function TableFilterSidebar({
	onApplyFilters,
	onClearFilters,
	hasActiveFilters,
	onClose,
	className,
}: TableFilterSidebarProps) {
	const [conditions, setConditions] = useState<FilterCondition[]>([]);

	const addCondition = () => {
		setConditions((prev) => [
			...prev,
			{
				id: generateId(),
				field: "",
				operator: "eq",
				value: "",
			},
		]);
	};

	const removeCondition = (id: string) => {
		setConditions((prev) => prev.filter((c) => c.id !== id));
	};

	const updateCondition = (id: string, updates: Partial<FilterCondition>) => {
		setConditions((prev) =>
			prev.map((c) => (c.id === id ? { ...c, ...updates } : c)),
		);
	};

	const buildWhereClause = (): Record<string, unknown> => {
		const where: Record<string, unknown> = {};

		for (const condition of conditions) {
			if (!condition.field.trim()) continue;

			let value: unknown;

			switch (condition.operator) {
				case "is_null":
					value = {
						is_null: getBooleanConditionValue(condition.value) === "true",
					};
					break;
				case "has_key":
					value = {
						has_key: getBooleanConditionValue(condition.value) === "true",
					};
					break;
				case "in":
					value = {
						in: condition.value.split(",").map((v) => v.trim()),
					};
					break;
				case "eq":
					value = condition.value;
					break;
				default:
					value = { [condition.operator]: condition.value };
			}

			where[condition.field] = value;
		}

		return where;
	};

	const handleApply = () => {
		const where = buildWhereClause();
		onApplyFilters(where);
	};

	const handleClear = () => {
		setConditions([]);
		onClearFilters();
	};

	const hasConditions = conditions.length > 0;

	return (
		<div
			className={cn(
				"flex h-full min-w-0 flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border bg-card",
				className,
			)}
		>
			<div className="flex items-center justify-between gap-3 border-b border-border/60 px-4 py-3">
				<div className="flex min-w-0 items-center gap-2">
					<Filter className="size-4 shrink-0 text-muted-foreground" />
					<span className="truncate font-medium text-sm">
						Filters
					</span>
				</div>
				<div className="flex items-center gap-1">
					{hasActiveFilters && (
						<Button
							type="button"
							variant="ghost"
							className="min-h-11 px-2"
							onClick={handleClear}
							aria-label="Clear filters"
						>
							<X className="size-4" />
							Clear
						</Button>
					)}
					{onClose && (
						<Button
							type="button"
							variant="ghost"
							size="icon-lg"
							onClick={onClose}
							title="Close filters"
							aria-label="Close filters"
						>
							<PanelLeftClose className="size-4" />
						</Button>
					)}
				</div>
			</div>

			{hasActiveFilters && (
				<div className="border-b border-border/60 bg-primary/5 px-4 py-2">
					<div className="text-sm text-muted-foreground">
						Active filters applied
					</div>
				</div>
			)}

			<div className="flex-1 overflow-auto">
				<FiltersSection
					conditions={conditions}
					onAdd={addCondition}
					onRemove={removeCondition}
					onUpdate={updateCondition}
				/>
			</div>

			{hasConditions && (
				<div className="border-t border-border/60 p-3">
					<Button type="button" onClick={handleApply} className="min-h-11 w-full">
						<Search className="size-4" />
						Apply Filters
					</Button>
				</div>
			)}
		</div>
	);
}

export default TableFilterSidebar;
