import { useComparisonLayout } from "@/hooks/useComparisonLayout";
import { DiffEditor } from "@monaco-editor/react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useBifrostMonacoTheme } from "@/hooks/useBifrostMonacoTheme";
import { useEditorStore, type DiffPreviewState } from "@/stores/editorStore";
import { SyncDiffHeader, SyncDiffResolution } from "./SyncDiffControls";

function getLanguage(path: string): string {
	if (path.endsWith(".json")) return "json";
	if (path.endsWith(".py")) return "python";
	if (/\.tsx?$/.test(path)) return "typescript";
	if (/\.jsx?$/.test(path)) return "javascript";
	if (/\.ya?ml$/.test(path)) return "yaml";
	return "plaintext";
}

export function SyncDiffView({ preview }: { preview: DiffPreviewState }) {
	const appearance = useBifrostMonacoTheme();
	const clearDiffPreview = useEditorStore((state) => state.clearDiffPreview);
	const { containerRef, wide } = useComparisonLayout();
	const isDeleteConflict =
		preview.conflictType === "deleted_by_us" ||
		preview.conflictType === "deleted_by_them";
	const sideBySide = wide && preview.isConflict && !isDeleteConflict;
	return (
		<section
			aria-label="File comparison"
			ref={containerRef}
			className="flex h-full min-h-0 min-w-0 flex-col bg-background"
		>
			<SyncDiffHeader preview={preview} onClose={clearDiffPreview} />
			<div className="shrink-0 border-b text-xs text-muted-foreground">
				{sideBySide ? (
					<div className="grid grid-cols-2">
						<span className="border-r px-3 py-2">Remote</span>
						<span className="px-3 py-2">Local</span>
					</div>
				) : (
					<p className="px-3 py-2">
						{preview.isConflict
							? "Remote → Local · Unified comparison"
							: "Last commit → Working changes"}
					</p>
				)}
			</div>
			<div className="min-h-0 min-w-0 flex-1">
				{preview.error ? (
					<div className="space-y-3 p-4">
						<p
							role="alert"
							className="text-sm text-destructive [overflow-wrap:anywhere]"
						>
							Couldn’t load comparison: {preview.error}
						</p>
						{preview.onRetry && (
							<Button
								type="button"
								variant="outline"
								className="min-h-11"
								onClick={preview.onRetry}
							>
								Retry comparison
							</Button>
						)}
					</div>
				) : preview.isLoading ? (
					<p
						role="status"
						className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground"
					>
						<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						Loading comparison…
					</p>
				) : (
					<DiffEditor
						height="100%"
						language={getLanguage(preview.path)}
						theme={appearance.theme}
						beforeMount={appearance.beforeMount}
						onMount={appearance.onMount}
						original={preview.remoteContent ?? ""}
						modified={preview.localContent ?? ""}
						options={{
							...appearance.options,
							readOnly: true,
							minimap: { enabled: false },
							scrollBeyondLastLine: false,
							renderSideBySide: sideBySide,
							wordWrap: "on",
							diffWordWrap: "on",
							lineNumbersMinChars: 3,
							scrollbar: { alwaysConsumeMouseWheel: false },
						}}
					/>
				)}
			</div>
			<SyncDiffResolution preview={preview} />
		</section>
	);
}
