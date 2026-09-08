import type { ReactNode } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

interface ReportRecordListProps {
	label: string;
	sort: { by: string; dir: "asc" | "desc" };
	onSort: (column: string) => void;
	columns: { key: string; label: string }[];
	records: {
		id: string;
		title: ReactNode;
		metrics: { label: string; value: ReactNode; fullWidth?: boolean }[];
	}[];
}

/** Compact report records preserve every metric without sideways reading. */
export function ReportRecordList({
	label,
	sort,
	onSort,
	columns,
	records,
}: ReportRecordListProps) {
	return (
		<section aria-label={label} className="min-w-0 space-y-3 lg:hidden">
			<div className="flex flex-col gap-2 sm:flex-row sm:items-center">
				<Select value={sort.by} onValueChange={onSort}>
					<SelectTrigger
						aria-label={`Sort ${label}`}
						className="h-11 min-h-11 w-full min-w-0 flex-1 rounded-[var(--bf-radius-control)]"
					>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{columns.map((column) => (
							<SelectItem key={column.key} value={column.key}>
								{column.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				<Button
					type="button"
					variant="outline"
					className="h-11 shrink-0 rounded-[var(--bf-radius-control)]"
					onClick={() => onSort(sort.by)}
					aria-label={`Sort ${sort.dir === "asc" ? "descending" : "ascending"}`}
				>
					{sort.dir === "asc" ? (
						<ArrowUp className="size-4" />
					) : (
						<ArrowDown className="size-4" />
					)}
					{sort.dir === "asc" ? "Ascending" : "Descending"}
				</Button>
			</div>
			<ul className="space-y-3">
				{records.map((record) => (
					<li
						key={record.id}
						className="space-y-3 rounded-[var(--bf-radius-control)] border border-border/70 bg-background p-3"
					>
						<h3 className="text-sm font-semibold leading-6 [overflow-wrap:anywhere]">
							{record.title}
						</h3>
						<dl className="grid grid-cols-2 gap-3">
							{record.metrics.map((metric, index) => (
								<div
									key={metric.label}
									className={
										index === 0 || metric.fullWidth
											? "min-w-0 col-span-2"
											: "min-w-0"
									}
								>
									<dt className="text-xs leading-5 text-muted-foreground">
										{metric.label}
									</dt>
									<dd
										className={`font-mono font-medium tabular-nums [overflow-wrap:anywhere] ${index === 0 ? "text-lg" : "text-sm"}`}
									>
										{metric.value}
									</dd>
								</div>
							))}
						</dl>
					</li>
				))}
			</ul>
		</section>
	);
}
