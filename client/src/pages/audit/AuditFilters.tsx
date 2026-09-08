import { useId } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
export type AuditFilterKey =
	"searchText" | "actionGroup" | "outcome" | "startDate" | "endDate";
const ACTION_GROUPS = [
	{ value: "All", label: "All actions" },
	{ value: "auth.", label: "Authentication" },
	{ value: "user.", label: "Users" },
	{ value: "role.", label: "Roles" },
	{ value: "organization.", label: "Organizations" },
	{ value: "policy.deny", label: "Policy denials" },
];

const OUTCOMES = [
	{ value: "All", label: "All outcomes" },
	{ value: "success", label: "Success" },
	{ value: "failure", label: "Failure" },
];

export function AuditFilters({
	searchText,
	actionGroup,
	outcome,
	startDate,
	endDate,
	hasActiveFilters,
	onChange,
	onClear,
}: Record<AuditFilterKey, string> & {
	hasActiveFilters: boolean;
	onChange: (key: AuditFilterKey, value: string) => void;
	onClear: () => void;
}) {
	const dateErrorId = useId();
	const invalidDateRange = Boolean(
		startDate && endDate && startDate > endDate,
	);
	return (
		<>
			{/* Filters */}
			<div className="space-y-3 [&_input]:min-h-11 [&_button]:min-h-11">
				<Input
					type="search"
					aria-label="Search audit events"
					placeholder="Search path, table, action, or IP…"
					value={searchText}
					onChange={(e) => onChange("searchText", e.target.value)}
					className="w-full"
				/>

				<div className="grid gap-3 sm:grid-cols-2 lg:flex lg:flex-wrap lg:items-center">
					<Select
						value={actionGroup}
						onValueChange={(value) =>
							onChange("actionGroup", value)
						}
					>
						<SelectTrigger
							className="w-full lg:w-[200px]"
							aria-label="Action filter"
						>
							<SelectValue placeholder="Action" />
						</SelectTrigger>
						<SelectContent>
							{ACTION_GROUPS.map((g) => (
								<SelectItem
									className="min-h-11"
									key={g.value}
									value={g.value}
								>
									{g.label}
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					<Select
						value={outcome}
						onValueChange={(value) => onChange("outcome", value)}
					>
						<SelectTrigger
							className="w-full lg:w-[160px]"
							aria-label="Outcome filter"
						>
							<SelectValue placeholder="Outcome" />
						</SelectTrigger>
						<SelectContent>
							{OUTCOMES.map((o) => (
								<SelectItem
									className="min-h-11"
									key={o.value}
									value={o.value}
								>
									{o.label}
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					<div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2 gap-y-2 sm:col-span-2 lg:ml-auto lg:flex">
						<span className="text-sm text-muted-foreground">
							From
						</span>
						<Input
							type="date"
							aria-label="Start date"
							aria-invalid={invalidDateRange}
							aria-describedby={
								invalidDateRange ? dateErrorId : undefined
							}
							value={startDate}
							max={endDate || undefined}
							onChange={(e) =>
								onChange("startDate", e.target.value)
							}
							className="min-w-0 lg:w-[150px]"
						/>
						<span className="text-sm text-muted-foreground">
							To
						</span>
						<Input
							type="date"
							aria-label="End date"
							aria-invalid={invalidDateRange}
							aria-describedby={
								invalidDateRange ? dateErrorId : undefined
							}
							value={endDate}
							min={startDate || undefined}
							onChange={(e) =>
								onChange("endDate", e.target.value)
							}
							className="min-w-0 lg:w-[150px]"
						/>
					</div>

					{hasActiveFilters && (
						<Button
							variant="ghost"
							onClick={onClear}
							className="justify-self-start lg:shrink-0"
						>
							Clear filters
						</Button>
					)}
				</div>
				{invalidDateRange && (
					<p
						id={dateErrorId}
						role="alert"
						className="text-sm text-destructive"
					>
						End date must be on or after start date.
					</p>
				)}
			</div>
		</>
	);
}
