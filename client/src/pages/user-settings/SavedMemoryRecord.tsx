import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TiptapEditor } from "@/components/ui/tiptap-editor";
import type { MemoryEntry } from "@/services/memory";

export function SavedMemoryRecord({
	memory,
	onRemove,
}: {
	memory: MemoryEntry;
	onRemove: () => void;
}) {
	return (
		<div className="min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)]">
			<TiptapEditor
				content={memory.content}
				readOnly
				ariaLabel="Saved memory"
				className="min-w-0 border-0 [overflow-wrap:anywhere]"
				editorClassName="min-h-0 p-0"
			/>
			<div className="flex items-center justify-between gap-3">
				<p className="min-w-0 text-xs text-muted-foreground">
					Remembered{" "}
					<time dateTime={memory.created_at}>
						{new Date(memory.created_at).toLocaleString()}
					</time>
				</p>
				<Button
					type="button"
					variant="ghost"
					size="icon-lg"
					aria-label="Remove memory"
					onClick={onRemove}
				>
					<Trash2 aria-hidden="true" className="size-4" />
				</Button>
			</div>
		</div>
	);
}
