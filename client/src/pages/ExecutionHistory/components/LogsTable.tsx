import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableFooter,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { LogLevel, LogRecord } from "./LogRecord";
import { PaginationFooter } from "@/components/pagination/PaginationFooter";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import type { components } from "@/lib/v1";
import { formatDate } from "@/lib/utils";

type LogListEntry = components["schemas"]["LogListEntry"];

interface LogsTableProps {
	logs: LogListEntry[];
	isLoading: boolean;
	isFetching?: boolean;
	continuationToken?: string | null;
	onNextPage: () => void;
	onPrevPage: () => void;
	canGoBack: boolean;
	currentPage: number;
	onLogClick: (log: LogListEntry) => void;
}

export function LogsTable({
	logs,
	isLoading,
	isFetching = false,
	continuationToken,
	onNextPage,
	onPrevPage,
	canGoBack,
	currentPage,
	onLogClick,
}: LogsTableProps) {
	const isDesktop = useIsDesktop();
	if (isLoading)
		return (
			<div
				role="status"
				aria-busy="true"
				className="rounded-[var(--bf-radius-surface)] border border-border bg-card p-6 text-sm text-muted-foreground"
			>
				Loading logs…
			</div>
		);

	const paginationFooter = (className?: string) => (
		<PaginationFooter
			aria-label="Log pages"
			className={className}
			summary={`Page ${currentPage}`}
			pending={isFetching}
			previousDisabled={!canGoBack || isFetching}
			nextDisabled={!continuationToken || isFetching}
			onPrevious={onPrevPage}
			onNext={onNextPage}
		/>
	);

	return (
		<div className="flex min-h-0 min-w-0 flex-col gap-4 lg:flex-1">
			{logs.length === 0 ? (
				<div
					className="rounded-[var(--bf-radius-surface)] border border-border bg-card p-6 text-center text-sm text-muted-foreground"
					aria-live="polite"
				>
					No logs found matching your filters.
				</div>
			) : !isDesktop ? (
				<ul
					aria-label="Log records"
					className="divide-y divide-border rounded-[var(--bf-radius-surface)] border border-border bg-card lg:min-h-0 lg:flex-1 lg:overflow-auto xl:overflow-visible"
				>
					{logs.map((log) => (
						<LogRecord key={log.id} log={log} onOpen={onLogClick} />
					))}
				</ul>
			) : (
				<DataTable
					className="[&_table]:table-fixed"
					aria-busy={isFetching ? "true" : undefined}
				>
					<DataTableHeader>
						<DataTableRow>
							<DataTableHead className="w-[150px]">
								Organization
							</DataTableHead>
							<DataTableHead className="w-[180px]">
								Workflow
							</DataTableHead>
							<DataTableHead className="w-[120px]">
								Level
							</DataTableHead>
							<DataTableHead>Message</DataTableHead>
							<DataTableHead className="w-[220px]">
								Timestamp
							</DataTableHead>
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{logs.map((log) => (
							<DataTableRow
								key={log.id}
								clickable
								href={`/history/${log.execution_id}`}
								onClick={(event) => {
									if (
										event.metaKey ||
										event.ctrlKey ||
										event.shiftKey ||
										event.altKey ||
										event.button !== 0
									)
										return;
									onLogClick(log);
								}}
							>
								<DataTableCell className="font-medium [overflow-wrap:anywhere]">
									{log.organization_name || "—"}
								</DataTableCell>
								<DataTableCell className="[overflow-wrap:anywhere]">
									{log.workflow_name}
								</DataTableCell>
								<DataTableCell>
									<LogLevel level={log.level} />
								</DataTableCell>
								<DataTableCell title={log.message}>
									<p className="line-clamp-3 whitespace-pre-wrap font-mono text-sm leading-relaxed [overflow-wrap:anywhere]">
										{log.message}
									</p>
								</DataTableCell>
								<DataTableCell className="text-sm text-muted-foreground">
									{formatDate(log.timestamp)}
								</DataTableCell>
							</DataTableRow>
						))}
					</DataTableBody>
					<DataTableFooter>
						<DataTableRow>
							<DataTableCell colSpan={5} className="p-0">
								{paginationFooter("px-6")}
							</DataTableCell>
						</DataTableRow>
					</DataTableFooter>
				</DataTable>
			)}
			{(logs.length === 0 || !isDesktop) && paginationFooter()}
		</div>
	);
}
