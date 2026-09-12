import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TiptapEditor } from "@/components/ui/tiptap-editor";
import { FormConfirmationMarkdown } from "./FormConfirmation";

interface FormConfirmationEditorProps {
	value: string;
	savedValue: string;
	view: "edit" | "preview";
	pending: boolean;
	error: boolean;
	onView: (view: "edit" | "preview") => void;
	onChange: (value: string) => void;
	onSave: () => void;
}

export function FormConfirmationEditor({ value, savedValue, view, pending, error, onView, onChange, onSave }: FormConfirmationEditorProps) {
	const id = useId();
	return (
		<section aria-labelledby={id} className="min-w-0 space-y-4 border-t pt-[var(--bf-surface-pad)]">
			<div className="space-y-1"><h3 id={id} className="text-sm font-medium">Confirmation Message</h3><p className="text-sm text-muted-foreground">Shown after a successful anonymous submission.</p></div>
			<Tabs value={view} onValueChange={value => onView(value as "edit" | "preview")}>
				<TabsList className="grid w-full grid-cols-2 group-data-horizontal/tabs:h-auto"><TabsTrigger value="edit" className="min-h-11">Edit</TabsTrigger><TabsTrigger value="preview" className="min-h-11">Preview</TabsTrigger></TabsList>
				<TabsContent value="edit" forceMount className="min-w-0 pt-2 data-[state=inactive]:hidden">
					<TiptapEditor content={value} onChange={onChange} ariaLabel="Confirmation Message editor" placeholder="Write a confirmation message…" className="min-h-[220px]" />
				</TabsContent>
				<TabsContent value="preview" forceMount className="min-w-0 pt-2 data-[state=inactive]:hidden">
					<div className="prose prose-sm min-h-[220px] max-w-none rounded-[var(--bf-radius-surface)] border bg-muted/20 p-[var(--bf-surface-pad)] [overflow-wrap:anywhere] dark:prose-invert"><FormConfirmationMarkdown markdown={value} /></div>
				</TabsContent>
			</Tabs>
			<p className="text-sm text-muted-foreground">Markdown and HTTPS images are supported. External image hosts receive a request when visitors view the confirmation.</p>
			{error && <p role="alert" className="text-sm text-destructive">Could not save the Confirmation Message. Your draft is still here; try again.</p>}
			{pending && <p role="status" className="text-sm text-muted-foreground">Saving Confirmation Message…</p>}
			<div className="flex justify-end"><Button type="button" className="min-h-11 w-full sm:w-auto" disabled={pending || value === savedValue} onClick={onSave}>{pending ? "Updating…" : error ? "Retry update" : "Update"}</Button></div>
		</section>
	);
}
