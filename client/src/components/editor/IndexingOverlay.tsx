import { useEditorStore } from "@/stores/editorStore";
import { Loader2 } from "lucide-react";

/**
 * Overlay that blocks the editor during ID injection/indexing operations.
 *
 * When saving a Python file for the first time, the server may inject
 * workflow/data_provider/tool IDs into decorators. During this operation,
 * the editor is blocked to prevent the user from typing while the content
 * is being modified server-side.
 *
 * The overlay displays:
 * - A semi-transparent background
 * - A spinner with a friendly message
 * - The message is customizable via the store
 */
export function IndexingOverlay() {
	const isIndexing = useEditorStore((state) => state.isIndexing);
	const indexingMessage = useEditorStore((state) => state.indexingMessage);

	if (!isIndexing) {
		return null;
	}

	return (
		<div className="absolute inset-0 z-50 flex items-center justify-center overflow-auto p-4 bg-background/80 backdrop-blur-sm">
			<div
				role="status"
				className="flex min-w-0 max-w-full flex-col items-center gap-3 rounded-[var(--bf-radius-surface)] border border-border bg-card p-4 text-center shadow-lg [overflow-wrap:anywhere]"
			>
				<Loader2 className="h-8 w-8 shrink-0 motion-safe:animate-spin text-primary" />
				<div className="text-center">
					<p className="text-sm font-medium">
						{indexingMessage || "Indexing workflow…"}
					</p>
					<p className="text-sm leading-5 text-muted-foreground mt-1">
						The editor will be available when indexing finishes.
					</p>
				</div>
			</div>
		</div>
	);
}
