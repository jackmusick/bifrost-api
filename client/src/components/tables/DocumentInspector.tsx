import { useState } from "react";
import {
	Braces,
	ChevronDown,
	ChevronRight,
	FileJson,
	Pencil,
	Trash2,
	X,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

import { HoverCopyText } from "@/components/common/HoverCopyText";
import { PrettyInputDisplay } from "@/components/execution/PrettyInputDisplay";
import { VariablesTreeView } from "@/components/ui/variables-tree-view";
import { Button } from "@/components/ui/button";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { DocumentPublic } from "@/services/tables";
import { DocumentDialog } from "./DocumentDialog";

interface DocumentInspectorProps {
	document: DocumentPublic | undefined;
	tableId: string;
	editing: boolean;
	onEdit: () => void;
	onClose: () => void;
	onBusyChange?: (busy: boolean) => void;
	onDelete?: () => void;
}

const jsonTheme = {
	'code[class*="language-"]': {
		color: "var(--foreground)",
		background: "transparent",
		fontFamily: "var(--font-mono)",
	},
	'pre[class*="language-"]': {
		color: "var(--foreground)",
		background: "var(--muted)",
	},
	property: { color: "var(--primary)" },
	string: { color: "var(--bf-success)" },
	number: { color: "var(--bf-info)" },
	boolean: { color: "var(--bf-info)" },
	null: { color: "var(--muted-foreground)" },
	punctuation: { color: "var(--muted-foreground)" },
};

function formatDate(value: string | null | undefined): string {
	if (!value) return "—";
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return "—";
	return date.toLocaleString(undefined, {
		year: "numeric",
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function documentData(document: DocumentPublic | undefined) {
	return ((document?.data ?? {}) as Record<string, unknown>) ?? {};
}

function Metadata({ document }: { document: DocumentPublic | undefined }) {
	const [open, setOpen] = useState(false);
	const metadata: Record<string, unknown> = {
		created_at: formatDate(document?.created_at),
		updated_at: formatDate(document?.updated_at),
		created_by: document?.created_by ?? "—",
		updated_by: document?.updated_by ?? "—",
	};
	return (
		<Collapsible
			open={open}
			onOpenChange={setOpen}
			className="shrink-0 border-t px-4 py-2"
		>
			<CollapsibleTrigger className="flex min-h-10 w-full items-center justify-between gap-3 rounded-[var(--bf-radius-control)] text-left text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none">
				<span>Metadata</span>
				{open ? (
					<ChevronDown aria-hidden="true" className="size-4" />
				) : (
					<ChevronRight aria-hidden="true" className="size-4" />
				)}
			</CollapsibleTrigger>
			<CollapsibleContent>
				<div className="max-h-40 overflow-y-auto pt-1">
					<VariablesTreeView data={metadata} />
				</div>
			</CollapsibleContent>
		</Collapsible>
	);
}

export function DocumentInspector({
	document,
	tableId,
	editing,
	onEdit,
	onClose,
	onBusyChange,
	onDelete,
}: DocumentInspectorProps) {
	if (editing) {
		return (
			<DocumentDialog
				document={document}
				tableId={tableId}
				open
				onClose={onClose}
				embedded
				onBusyChange={onBusyChange}
			/>
		);
	}

	const data = documentData(document);
	const json = JSON.stringify(data, null, 2);
	const title = document ? "Document" : "New document";

	return (
		<section
			className="flex min-h-0 flex-1 flex-col overflow-hidden"
			aria-label={title}
		>
			<header className="flex shrink-0 items-start justify-between gap-3 border-b bg-muted/20 px-4 py-3">
				<div className="flex min-w-0 items-start gap-3">
					<FileJson
						aria-hidden="true"
						className="mt-1 size-5 shrink-0 text-primary"
					/>
					<div className="min-w-0">
						<h2 className="text-sm font-semibold leading-6">
							{title}
						</h2>
						{document && (
							<HoverCopyText
								value={document.id}
								label="Document ID"
								className="mt-1 block text-muted-foreground"
							/>
						)}
					</div>
				</div>
				<Button
					type="button"
					variant="ghost"
					size="icon"
					className="shrink-0"
					onClick={onClose}
					aria-label="Close document inspector"
				>
					<X aria-hidden="true" className="size-4" />
				</Button>
			</header>

			<div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
				<div className="min-h-0">
					<Tabs defaultValue="data" className="min-w-0 gap-1">
						<TabsList variant="line">
							<TabsTrigger value="data">
								<Braces aria-hidden="true" className="size-4" />
								Data
							</TabsTrigger>
							<TabsTrigger value="json">
								<FileJson
									aria-hidden="true"
									className="size-4"
								/>
								JSON
							</TabsTrigger>
						</TabsList>
						<TabsContent value="data" className="min-w-0 pt-2">
							{Object.keys(data).length ? (
								<div className="[&>div]:space-y-1 [&>div>div:first-child]:-mb-1">
									<PrettyInputDisplay
										inputData={data}
										context="result"
										showToggle={false}
										showDescription={false}
									/>
								</div>
							) : (
								<p className="rounded-[var(--bf-radius-surface)] border bg-muted/20 p-3 text-sm text-muted-foreground">
									This document has no data yet.
								</p>
							)}
						</TabsContent>
						<TabsContent value="json" className="min-w-0 pt-2">
							<SyntaxHighlighter
								language="json"
								style={jsonTheme}
								tabIndex={0}
								aria-label="Document JSON"
								wrapLongLines
								className="border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								customStyle={{
									margin: 0,
									borderRadius: "var(--bf-radius-surface)",
									padding: "1rem",
									overflowWrap: "anywhere",
									whiteSpace: "pre-wrap",
									fontSize: "0.8125rem",
									lineHeight: "1.5",
								}}
								codeTagProps={{
									style: {
										fontFamily: "var(--font-mono)",
										whiteSpace: "pre-wrap",
										overflowWrap: "anywhere",
									},
								}}
							>
								{json}
							</SyntaxHighlighter>
						</TabsContent>
					</Tabs>
				</div>
			</div>

			<Metadata document={document} />

			<footer className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t px-4 py-3">
				{document && onDelete && (
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						onClick={onDelete}
					>
						<Trash2 aria-hidden="true" className="size-4" />
						Delete
					</Button>
				)}
				<Button type="button" className="min-h-11" onClick={onEdit}>
					<Pencil aria-hidden="true" className="size-4" />
					Edit
				</Button>
			</footer>
		</section>
	);
}
