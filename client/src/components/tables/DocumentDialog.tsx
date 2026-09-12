import { useState, useMemo, useRef, useEffect, type RefObject } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useBifrostMonacoTheme } from "@/hooks/useBifrostMonacoTheme";
import {
	useInsertDocument,
	useUpdateDocument,
	type DocumentPublic,
} from "@/services/tables";

import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Database, X } from "lucide-react";

interface DocumentDialogProps {
	returnFocusRef?: RefObject<HTMLElement | null>;
	document?: DocumentPublic | undefined;
	tableId: string;
	open: boolean;
	onClose: () => void;
	embedded?: boolean;
	onBusyChange?: (busy: boolean) => void;
}

function parseDocument(
	value: string,
):
	| { data: Record<string, unknown>; error: null }
	| { data: null; error: string } {
	if (!value.trim())
		return { data: null, error: "Enter a JSON object for this document." };
	try {
		const data: unknown = JSON.parse(value);
		if (data === null || typeof data !== "object" || Array.isArray(data))
			return {
				data: null,
				error: 'Document data must be a JSON object, such as {"name": "Example"}.',
			};
		return { data: data as Record<string, unknown>, error: null };
	} catch {
		return {
			data: null,
			error: "Check the JSON syntax. Property names and text values need double quotes.",
		};
	}
}

/** Each table/document/open session owns its draft and pending request. */
export function DocumentDialog(props: DocumentDialogProps) {
	return (
		<DocumentDialogSession
			key={`${props.tableId}:${props.document?.id ?? "new"}:${props.open}`}
			{...props}
		/>
	);
}

function DocumentDialogSession({
	document,
	tableId,
	open,
	onClose,
	returnFocusRef,
	embedded = false,
	onBusyChange,
}: DocumentDialogProps) {
	const returnFocus = useDialogReturnFocus(returnFocusRef, true);
	const insertDocument = useInsertDocument();
	const updateDocument = useUpdateDocument();
	const appearance = useBifrostMonacoTheme();
	const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
	const pendingRef = useRef(false);
	const active = useRef(true);
	const [pending, setPending] = useState(false);
	const [saveError, setSaveError] = useState(false);
	const saveErrorRef = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		onBusyChange?.(pending);
	}, [onBusyChange, pending]);
	useEffect(() => {
		if (saveError) {
			saveErrorRef.current?.focus();
			saveErrorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [saveError]);
	const [jsonValue, setJsonValue] = useState(() =>
		document ? JSON.stringify(document.data, null, 2) : "{\n  \n}",
	);
	const parsed = useMemo(() => parseDocument(jsonValue), [jsonValue]);
	const isEditing = !!document;
	useEffect(() => {
		active.current = true;
		return () => {
			active.current = false;
		};
	}, []);
	const close = () => {
		if (!pendingRef.current) onClose();
	};
	const handleMount: OnMount = (editor, monaco) => {
		editorRef.current = editor;
		appearance.onMount(editor, monaco);
		editor.focus();
	};
	async function save() {
		if (pendingRef.current || parsed.error !== null) return;
		pendingRef.current = true;
		setPending(true);
		setSaveError(false);
		try {
			if (document)
				await updateDocument.mutateAsync({
					params: {
						path: { table_id: tableId, doc_id: document.id },
					},
					body: { data: parsed.data },
				});
			else
				await insertDocument.mutateAsync({
					params: { path: { table_id: tableId } },
					body: { data: parsed.data, upsert: false },
				});
			if (active.current) onClose();
		} catch {
			if (active.current) setSaveError(true);
		} finally {
			pendingRef.current = false;
			if (active.current) setPending(false);
		}
	}
	const title = isEditing ? "Edit Document" : "Create Document";
	const description = isEditing
		? "Update the document data. Changes merge with the existing record."
		: "Add a new document to this table.";
	const content = (
		<>
			{embedded ? (
				<header className="flex shrink-0 items-start justify-between gap-3 border-b bg-muted/20 px-4 py-3">
					<div className="flex min-w-0 items-start gap-3">
						<Database
							aria-hidden="true"
							className="mt-1 size-5 shrink-0 text-primary"
						/>
						<div className="min-w-0">
							<h2 className="text-sm font-semibold leading-6 [overflow-wrap:anywhere]">
								{title}
							</h2>
							<p className="mt-1 text-sm text-muted-foreground">
								{description}
							</p>
						</div>
					</div>
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="shrink-0"
						disabled={pending}
						onClick={close}
						aria-label="Close document editor"
					>
						<X aria-hidden="true" className="size-4" />
					</Button>
				</header>
			) : (
				<DialogHeader className="shrink-0 p-[var(--bf-surface-pad)] pr-14 text-left">
					<DialogTitle>{title}</DialogTitle>
					<DialogDescription>{description}</DialogDescription>
				</DialogHeader>
			)}
			<div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-[var(--bf-surface-pad)] pb-4">
				<div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
					<p className="text-sm font-medium">Document Data (JSON)</p>
					<Button
						type="button"
						variant="ghost"
						className="min-h-11"
						disabled={pending}
						onClick={() => {
							if (!pendingRef.current)
								void editorRef.current
									?.getAction("editor.action.formatDocument")
									?.run();
						}}
					>
						Format
					</Button>
				</div>
				<div className="min-h-24 flex-1 overflow-hidden rounded-[var(--bf-radius-surface)] border">
					<Editor
						height="100%"
						language="json"
						value={jsonValue}
						onChange={(value) => {
							if (!pendingRef.current) {
								setJsonValue(value ?? "");
								setSaveError(false);
							}
						}}
						onMount={handleMount}
						theme={appearance.theme}
						beforeMount={appearance.beforeMount}
						options={{
							...appearance.options,
							ariaLabel: "Document data (JSON)",
							readOnly: pending,
							minimap: { enabled: false },
							scrollBeyondLastLine: false,
							fontSize: 13,
							wordWrap: "on",
							automaticLayout: true,
							tabSize: 2,
							insertSpaces: true,
							formatOnPaste: true,
							autoClosingBrackets: "always",
							autoClosingQuotes: "always",
							bracketPairColorization: { enabled: true },
							folding: true,
							foldingStrategy: "indentation",
							lineNumbers: "on",
							renderWhitespace: "selection",
							quickSuggestions: false,
							suggestOnTriggerCharacters: false,
							padding: { top: 12, bottom: 12 },
						}}
						loading={
							<div
								role="status"
								className="flex h-full items-center justify-center p-4 text-sm text-muted-foreground"
							>
								Loading editor…
							</div>
						}
					/>
				</div>
				{parsed.error && (
					<p
						role="alert"
						className="shrink-0 text-sm text-destructive"
					>
						{parsed.error}
					</p>
				)}
				{saveError && (
					<p
						ref={saveErrorRef}
						tabIndex={-1}
						role="alert"
						className="shrink-0 text-sm text-destructive outline-none"
					>
						Document could not be saved. Your JSON is preserved. Try
						again.
					</p>
				)}
			</div>
			<DialogFooter className="shrink-0 border-t p-[var(--bf-surface-pad)]">
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					onClick={close}
					disabled={pending}
				>
					Cancel
				</Button>
				<Button
					type="button"
					className="min-h-11"
					disabled={pending || parsed.error !== null}
					onClick={() => void save()}
				>
					{pending
						? "Saving..."
						: saveError
							? "Retry save"
							: isEditing
								? "Update"
								: "Create"}
				</Button>
			</DialogFooter>
		</>
	);

	if (embedded) {
		if (!open) return null;
		return (
			<section
				className="flex min-h-0 flex-1 flex-col overflow-hidden"
				aria-busy={pending}
				aria-label={title}
			>
				{content}
			</section>
		);
	}

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next) close();
			}}
		>
			<DialogContent
				{...returnFocus}
				className="flex h-[min(44rem,calc(100dvh-2rem))] max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-[700px]"
				showCloseButton={!pending}
				onEscapeKeyDown={(event) => {
					if (pendingRef.current) event.preventDefault();
				}}
				aria-busy={pending}
			>
				{content}
			</DialogContent>
		</Dialog>
	);
}
