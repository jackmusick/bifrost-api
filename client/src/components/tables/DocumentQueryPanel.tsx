import { useState } from "react";
import { Plus, Trash2, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { QueryOperator } from "@/services/tables";

interface FilterCondition {
	id: string;
	field: string;
	operator: QueryOperator;
	value: string;
}

interface DocumentQueryPanelProps {
	onApplyFilters: (where: Record<string, unknown>) => void;
	onClearFilters: () => void;
	hasActiveFilters: boolean;
}

const OPERATORS: { value: QueryOperator; label: string }[] = [
	{ value: "eq", label: "equals" },
	{ value: "ne", label: "not equals" },
	{ value: "contains", label: "contains" },
	{ value: "starts_with", label: "starts with" },
	{ value: "ends_with", label: "ends with" },
	{ value: "gt", label: "greater than" },
	{ value: "gte", label: "greater or equal" },
	{ value: "lt", label: "less than" },
	{ value: "lte", label: "less or equal" },
	{ value: "in", label: "in list (comma separated)" },
	{ value: "is_null", label: "is null" },
	{ value: "has_key", label: "has field" },
];

function generateId() {
	return Math.random().toString(36).substring(2, 9);
}

export function DocumentQueryPanel({
	onApplyFilters,
	onClearFilters,
	hasActiveFilters,
}: DocumentQueryPanelProps) {
	const [conditions, setConditions] = useState<FilterCondition[]>([]);
	const [isExpanded, setIsExpanded] = useState(false);

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
		setIsExpanded(true);
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
					value = { is_null: (condition.value || "true") === "true" };
					break;
				case "has_key":
					value = { has_key: (condition.value || "true") === "true" };
					break;
				case "in":
					value = {
						in: condition.value.split(",").map((v) => v.trim()),
					};
					break;
				case "eq":
					// Simple equality - just use the value directly
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

	return (
		<Card className="rounded-[var(--bf-radius-surface)] border bg-card">
			<CardHeader className="py-3">
				<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<CardTitle className="flex items-center gap-2 text-sm font-medium">
						<Search className="h-4 w-4" />
						Query Filters
						{hasActiveFilters && (
							<Badge variant="secondary" className="ml-2">
								Active
							</Badge>
						)}
					</CardTitle>
					<div className="flex flex-wrap items-center gap-2">
						{hasActiveFilters && (
							<Button
								variant="ghost"
								size="sm"
								onClick={handleClear}
								className="min-h-11"
							>
								<X className="h-4 w-4 mr-1" />
								Clear
							</Button>
						)}
						<Button
							variant="outline"
							size="sm"
							onClick={addCondition}
							className="min-h-11"
						>
							<Plus className="h-4 w-4 mr-1" />
							Add Filter
						</Button>
					</div>
				</div>
			</CardHeader>

			{(isExpanded || conditions.length > 0) && (
				<CardContent className="pt-0">
					<div className="space-y-3">
						{conditions.map((condition) => (
							<div
								key={condition.id}
								className="rounded-[var(--bf-radius-control)] border border-border/70 bg-background p-3"
							>
								<div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_180px_minmax(0,1fr)_auto] md:items-center">
									<Input
										aria-label="Field name"
										placeholder="Field name (e.g., status)"
										value={condition.field}
										onChange={(e) =>
											updateCondition(condition.id, {
												field: e.target.value,
											})
										}
										className="min-h-11 min-w-0"
									/>
									<Select
										value={condition.operator}
										onValueChange={(value: QueryOperator) =>
											updateCondition(condition.id, {
												operator: value,
											})
										}
									>
										<SelectTrigger aria-label="Filter operator" className="h-11 min-h-11 w-full min-w-0 rounded-[var(--bf-radius-control)]">
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
											value={condition.value || "true"}
											onValueChange={(value) =>
												updateCondition(condition.id, {
													value,
												})
											}
										>
											<SelectTrigger aria-label="Filter value" className="h-11 min-h-11 w-full min-w-0 rounded-[var(--bf-radius-control)]">
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
											aria-label="Filter value"
											placeholder="Value"
											value={condition.value}
											onChange={(e) =>
												updateCondition(condition.id, {
													value: e.target.value,
												})
											}
											className="min-h-11 min-w-0"
										/>
									)}
									<Button
										variant="ghost"
										size="icon"
										className="h-11 w-11 shrink-0"
										aria-label="Remove filter"
										onClick={() =>
											removeCondition(condition.id)
										}
									>
										<Trash2 className="h-4 w-4" />
									</Button>
								</div>
							</div>
						))}

						{conditions.length > 0 && (
							<div className="flex justify-end pt-2">
								<Button onClick={handleApply} className="min-h-11">
									<Search className="h-4 w-4 mr-2" />
									Apply Filters
								</Button>
							</div>
						)}
					</div>
				</CardContent>
			)}
		</Card>
	);
}
