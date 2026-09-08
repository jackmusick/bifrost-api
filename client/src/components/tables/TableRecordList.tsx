import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Checkbox } from "@/components/ui/checkbox";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import type { TablePublic } from "@/services/tables";

interface TableRecordListProps {
	tables: TablePublic[];
	isPlatformAdmin: boolean;
	selectedIds: Set<string>;
	allVisibleSelected: boolean;
	someVisibleSelected: boolean;
	onToggleAll: () => void;
	onToggle: (id: string) => void;
	scopeName: (id: string | null | undefined) => string;
	formatDate: (date: string | null) => string;
	renderActions: (table: TablePublic) => ReactNode;
}

export function TableRecordList({
	tables,
	isPlatformAdmin,
	selectedIds,
	allVisibleSelected,
	someVisibleSelected,
	onToggleAll,
	onToggle,
	scopeName,
	formatDate,
	renderActions,
}: TableRecordListProps) {
	return (
		<div className="min-w-0 space-y-3">
			{isPlatformAdmin && (
				<label className="flex min-h-11 w-fit cursor-pointer items-center gap-3 text-sm">
					<Checkbox
						aria-label="Select visible tables"
						checked={
							allVisibleSelected
								? true
								: someVisibleSelected
									? "indeterminate"
									: false
						}
						onCheckedChange={onToggleAll}
					/>
					Select visible tables
				</label>
			)}
			<ul
				aria-label="Data tables"
				className="divide-y rounded-[var(--bf-radius-surface)] border bg-card"
			>
				{tables.map((table) => (
					<li key={table.id} className="space-y-3 p-4">
						<h2 className="font-mono text-sm font-semibold">
							<Link
								to={`/tables/${table.id}`}
								className="flex min-h-11 items-center rounded-[var(--bf-radius-control)] [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							>
								{table.name}
							</Link>
						</h2>
						<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
							{table.description || "No description"}
						</p>
						<dl className="grid grid-cols-2 gap-3 text-sm">
							<div className="min-w-0">
								<dt className="text-xs text-muted-foreground">
									Scope
								</dt>
								<dd className="mt-1 [overflow-wrap:anywhere]">
									{table.organization_id
										? isPlatformAdmin
											? scopeName(table.organization_id)
											: "Organization"
										: "Global"}
								</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									Created
								</dt>
								<dd className="mt-1">
									{formatDate(table.created_at)}
								</dd>
							</div>
						</dl>
						{table.is_solution_managed && (
							<div className="flex flex-wrap items-center gap-2">
								<SolutionManagedBadge
									solutionId={table.solution_id}
								/>
								<span className="text-xs text-muted-foreground">
									Edits are managed through deployment.
								</span>
							</div>
						)}
						<div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
							{isPlatformAdmin && (
								<label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
									<Checkbox
										aria-label={`Select ${table.name}`}
										checked={selectedIds.has(table.id)}
										onCheckedChange={() =>
											onToggle(table.id)
										}
									/>
									Select
								</label>
							)}
							{renderActions(table)}
						</div>
					</li>
				))}
			</ul>
		</div>
	);
}
