import { FileJson, Calendar } from "lucide-react";
import { DocumentActionsMenu } from "./DocumentActionsMenu";
import { MarkdownContent } from "@/components/common/MarkdownContent";
import { HoverCopyText } from "@/components/common/HoverCopyText";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { cn } from "@/lib/utils";
import type { DocumentPublic } from "@/services/tables";

interface DocumentRecordListProps {
	documents: DocumentPublic[];
	dataColumns: string[];
	selectedId?: string;
	onOpen: (doc: DocumentPublic) => void;
	onEdit: (doc: DocumentPublic) => void;
	onDelete: (doc: DocumentPublic) => void;
	disabled?: boolean;
}

function FieldValue({ value }: { value: unknown }) {
	if (value === undefined)
		return <span className="text-muted-foreground">—</span>;
	if (value === null)
		return <span className="text-muted-foreground">null</span>;
	if (typeof value === "string")
		return (
			<MarkdownContent
				content={value}
				variant="preview"
				className="line-clamp-2 break-words"
			/>
		);
	if (typeof value === "object")
		return (
			<span className="text-xs text-muted-foreground">
				{Array.isArray(value)
					? `${value.length} items`
					: `${Object.keys(value).length} fields`}
			</span>
		);
	return <span className="tabular-nums">{String(value)}</span>;
}

function dateLabel(value: string | null | undefined) {
	return value ? new Date(value).toLocaleDateString() : "—";
}

/** Compare actual fields at roomy widths; narrow panes use compact record summaries. */
export function DocumentRecordList({
	documents,
	dataColumns,
	selectedId,
	onOpen,
	onEdit,
	onDelete,
	disabled,
}: DocumentRecordListProps) {
	const columns = dataColumns.slice(0, 3);
	return (
		<div className="@container flex min-h-0 min-w-0 flex-col">
			<div className="hidden min-h-0 flex-col @[700px]:flex">
				<DataTable className="rounded-none border-0">
					<DataTableHeader>
						<DataTableRow>
							<DataTableHead className="w-44">ID</DataTableHead>
							{columns.map((column) => (
								<DataTableHead key={column}>
									{column}
								</DataTableHead>
							))}
							<DataTableHead className="w-0 whitespace-nowrap">
								Created
							</DataTableHead>
							<DataTableHead className="w-0">
								<span className="sr-only">Actions</span>
							</DataTableHead>
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{documents.map((doc) => (
							<DataTableRow
								key={doc.id}
								clickable={!disabled}
								aria-label={`Open document ${doc.id}`}
								aria-selected={selectedId === doc.id}
								onClick={() => !disabled && onOpen(doc)}
								className={cn(
									selectedId === doc.id &&
										"tree-row-selected",
								)}
							>
								<DataTableCell className="w-44 max-w-44 align-top">
									<HoverCopyText
										value={doc.id}
										label="Document ID"
										className="block max-w-36 truncate font-mono text-xs text-muted-foreground"
									/>
								</DataTableCell>
								{columns.map((column) => (
									<DataTableCell
										key={column}
										className="max-w-64 align-top whitespace-normal"
									>
										<FieldValue value={doc.data[column]} />
									</DataTableCell>
								))}
								<DataTableCell className="w-0 whitespace-nowrap align-top text-xs text-muted-foreground">
									{dateLabel(doc.created_at)}
								</DataTableCell>
								<DataTableCell className="w-0 align-top">
									{!disabled && (
										<DocumentActionsMenu
											id={doc.id}
											onEdit={() => onEdit(doc)}
											onDelete={() => onDelete(doc)}
										/>
									)}
								</DataTableCell>
							</DataTableRow>
						))}
					</DataTableBody>
				</DataTable>
			</div>
			<ul
				aria-label="Document records"
				className="min-h-0 divide-y divide-border/70 overflow-y-auto @[700px]:hidden"
			>
				{documents.map((doc) => (
					<li
						key={doc.id}
						className={cn(
							"relative min-w-0 transition-colors hover:bg-muted/40",
							selectedId === doc.id && "tree-row-selected",
						)}
					>
						<button
							type="button"
							disabled={disabled}
							aria-label={`Open document ${doc.id}`}
							aria-pressed={selectedId === doc.id}
							onClick={() => onOpen(doc)}
							className="flex w-full min-w-0 gap-3 p-4 pr-14 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
						>
							<span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-primary/20 bg-primary/10 text-primary">
								<FileJson className="size-4" />
							</span>
							<span className="grid min-w-0 flex-1 grid-cols-2 gap-x-3 gap-y-2">
								{columns.map((column, i) => (
									<span
										key={column}
										className={cn(
											"min-w-0",
											i === 0
												? "col-span-2 block"
												: "block",
										)}
									>
										{i > 0 && (
											<span className="block text-xs text-muted-foreground">
												{column}
											</span>
										)}
										<span
											className={cn(
												"block text-sm",
												i === 0 && "font-medium",
											)}
										>
											<FieldValue
												value={doc.data[column]}
											/>
										</span>
									</span>
								))}
								{columns.length === 0 && (
									<span className="block text-sm font-medium">
										Empty Document
									</span>
								)}
								<span className="col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
									<Calendar className="size-3.5" />
									{dateLabel(doc.created_at)}
								</span>
							</span>
						</button>
						<div className="pb-3 pl-16 pr-4">
							<HoverCopyText
								value={doc.id}
								label="Document ID"
								className="block max-w-full truncate font-mono text-xs text-muted-foreground"
							/>
						</div>
						<div className="absolute right-2 top-2">
							{!disabled && (
								<DocumentActionsMenu
									id={doc.id}
									onEdit={() => onEdit(doc)}
									onDelete={() => onDelete(doc)}
								/>
							)}
						</div>
					</li>
				))}
			</ul>
		</div>
	);
}
