import { DocumentActionsMenu } from "./DocumentActionsMenu";
import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Check, Copy } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import type { DocumentPublic } from "@/services/tables";
import { copyToClipboard } from "@/lib/clipboard";

interface DocumentRecordListProps {
	documents: DocumentPublic[];
	dataColumns: string[];
	onEdit: (doc: DocumentPublic) => void;
	onDelete: (doc: DocumentPublic) => void;
}

type CopyState = {
	id: string;
	status: "copied" | "error";
};

function valueToText(value: unknown): string {
	if (value === null) return "null";
	if (value === undefined) return "—";
	if (typeof value === "string") return value;
	if (typeof value === "number" || typeof value === "boolean") {
		return String(value);
	}

	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
}

function formatDate(dateStr: string | null | undefined): string {
	if (!dateStr) return "—";

	const date = new Date(dateStr);
	if (Number.isNaN(date.getTime())) return "—";

	return date.toLocaleString(undefined, {
		year: "numeric",
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function CopyIdButton({
	id,
	copyState,
	onCopy,
}: {
	id: string;
	copyState: CopyState | null;
	onCopy: (id: string) => void;
}) {
	const copied = copyState?.id === id && copyState.status === "copied";

	return (
		<Button
			type="button"
			variant="outline"
			className="h-11 shrink-0 gap-2 px-3"
			onClick={() => onCopy(id)}
			aria-label={copied ? "Document ID copied" : "Copy document ID"}
			title={copied ? "Copied" : "Copy document ID"}
		>
			{copied ? (
				<Check aria-hidden="true" className="size-4" />
			) : (
				<Copy aria-hidden="true" className="size-4" />
			)}
			<span>{copied ? "Copied" : "Copy ID"}</span>
		</Button>
	);
}

function DocumentJsonDisclosure({ data }: { data: Record<string, unknown> }) {
	return (
		<details className="group">
			<summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 outline-none transition-colors duration-[var(--bf-motion-feedback)] hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none [&::-webkit-details-marker]:hidden">
				<span className="text-sm font-medium text-foreground">
					View full JSON
				</span>
				<ChevronDown
					aria-hidden="true"
					className="size-4 shrink-0 text-muted-foreground transition-transform duration-[var(--bf-motion-feedback)] group-open:rotate-180 motion-reduce:transition-none"
				/>
			</summary>
			<pre
				tabIndex={0}
				className="mt-2 max-h-72 overflow-auto rounded-[var(--bf-radius-control)] bg-muted/20 p-3 font-mono text-xs leading-6 whitespace-pre-wrap break-words text-foreground focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none"
			>
				{JSON.stringify(data, null, 2)}
			</pre>
		</details>
	);
}

function DocumentDesktopRow({
	doc,
	dataColumns,
	copyState,
	onCopy,
	onEdit,
	onDelete,
}: {
	doc: DocumentPublic;
	dataColumns: string[];
	copyState: CopyState | null;
	onCopy: (id: string) => void;
	onEdit: (doc: DocumentPublic) => void;
	onDelete: (doc: DocumentPublic) => void;
}) {
	const data = (doc.data ?? {}) as Record<string, unknown>;
	const visibleColumns = dataColumns.slice(0, 3);

	return (
		<DataTableRow>
			<DataTableCell className="min-w-0 align-top">
				<div className="space-y-2">
					<div className="flex flex-wrap items-center gap-2">
						<span className="select-text font-mono text-xs text-foreground [overflow-wrap:anywhere]">
							{doc.id}
						</span>
						<CopyIdButton
							id={doc.id}
							copyState={copyState}
							onCopy={onCopy}
						/>
					</div>
				</div>
			</DataTableCell>
			{visibleColumns.map((column) => (
				<DataTableCell
					key={column}
					className="min-w-[7.5rem] max-w-[12rem] align-top text-sm [overflow-wrap:anywhere] whitespace-normal"
				>
					<span className="line-clamp-3">
						{valueToText(data[column])}
					</span>
				</DataTableCell>
			))}
			<DataTableCell className="min-w-[12rem] max-w-[18rem] align-top">
				<DocumentJsonDisclosure data={data} />
			</DataTableCell>
			<DataTableCell className="min-w-[8rem] whitespace-normal align-top text-sm text-muted-foreground">
				{formatDate(doc.created_at)}
			</DataTableCell>
			<DataTableCell className="whitespace-nowrap align-top text-right">
				<DocumentActionsMenu
					id={doc.id}
					onEdit={() => onEdit(doc)}
					onDelete={() => onDelete(doc)}
				/>
			</DataTableCell>
		</DataTableRow>
	);
}

function DocumentMobileRecord({
	doc,
	dataColumns,
	copyState,
	onCopy,
	onEdit,
	onDelete,
}: {
	doc: DocumentPublic;
	dataColumns: string[];
	copyState: CopyState | null;
	onCopy: (id: string) => void;
	onEdit: (doc: DocumentPublic) => void;
	onDelete: (doc: DocumentPublic) => void;
}) {
	const data = (doc.data ?? {}) as Record<string, unknown>;
	const visibleColumns = dataColumns.slice(0, 3);

	return (
		<li className="space-y-4 rounded-[var(--bf-radius-surface)] border border-border bg-card px-[var(--bf-surface-pad)] py-[var(--bf-surface-pad)]">
			<div className="space-y-2">
				<p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
					Document ID
				</p>
				<div className="flex flex-wrap items-start gap-2">
					<span className="select-text font-mono text-xs leading-6 text-foreground [overflow-wrap:anywhere]">
						{doc.id}
					</span>
					<CopyIdButton
						id={doc.id}
						copyState={copyState}
						onCopy={onCopy}
					/>
				</div>
			</div>

			<dl className="grid gap-3 sm:grid-cols-2">
				{visibleColumns.map((column) => (
					<div key={column} className="min-w-0 space-y-1">
						<dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
							{column}
						</dt>
						<dd className="min-w-0 text-sm [overflow-wrap:anywhere] whitespace-normal text-foreground">
							{valueToText(data[column])}
						</dd>
					</div>
				))}
				<div className="min-w-0 space-y-1 sm:col-span-2">
					<dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
						Created
					</dt>
					<dd className="text-sm text-foreground">
						{formatDate(doc.created_at)}
					</dd>
				</div>
			</dl>

			<DocumentJsonDisclosure data={data} />

			<DocumentActionsMenu
				id={doc.id}
				onEdit={() => onEdit(doc)}
				onDelete={() => onDelete(doc)}
			/>
		</li>
	);
}

export function DocumentRecordList({
	documents,
	dataColumns,
	onEdit,
	onDelete,
}: DocumentRecordListProps) {
	const [copyState, setCopyState] = useState<CopyState | null>(null);

	useEffect(() => {
		if (!copyState) return;

		const timeout = window.setTimeout(
			() => {
				setCopyState(null);
			},
			copyState.status === "copied" ? 1600 : 2600,
		);

		return () => window.clearTimeout(timeout);
	}, [copyState]);

	const visibleColumns = useMemo(
		() => dataColumns.slice(0, 3),
		[dataColumns],
	);

	const handleCopy = async (id: string) => {
		const copied = await copyToClipboard(id);
		if (copied) {
			setCopyState({ id, status: "copied" });
			toast.success("Document ID copied");
			return;
		}

		setCopyState({ id, status: "error" });
		toast.error("Failed to copy document ID");
	};

	if (documents.length === 0) {
		return null;
	}

	return (
		<div className="@container flex min-w-0 flex-col gap-4 lg:min-h-0 lg:flex-1">
			<div className="hidden min-h-0 flex-1 flex-col @5xl:flex">
				<DataTable className="max-h-full">
					<DataTableHeader>
						<DataTableRow>
							<DataTableHead className="min-w-0">
								ID
							</DataTableHead>
							{visibleColumns.map((column) => (
								<DataTableHead key={column}>
									{column}
								</DataTableHead>
							))}
							<DataTableHead className="min-w-[12rem]">
								Data
							</DataTableHead>
							<DataTableHead className="whitespace-normal">
								Created
							</DataTableHead>
							<DataTableHead className="w-0 whitespace-nowrap text-right">
								Actions
							</DataTableHead>
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{documents.map((doc) => (
							<DocumentDesktopRow
								key={doc.id}
								doc={doc}
								dataColumns={dataColumns}
								copyState={copyState}
								onCopy={handleCopy}
								onEdit={onEdit}
								onDelete={onDelete}
							/>
						))}
					</DataTableBody>
				</DataTable>
			</div>

			<ul
				aria-label="Document records"
				className="@5xl:hidden space-y-3 lg:min-h-0 lg:overflow-auto"
			>
				{documents.map((doc) => (
					<DocumentMobileRecord
						key={doc.id}
						doc={doc}
						dataColumns={dataColumns}
						copyState={copyState}
						onCopy={handleCopy}
						onEdit={onEdit}
						onDelete={onDelete}
					/>
				))}
			</ul>
		</div>
	);
}
