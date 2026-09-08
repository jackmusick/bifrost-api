import { useRef, useState } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { AlertTriangle } from "lucide-react";
import { useBifrostMonacoTheme } from "@/hooks/useBifrostMonacoTheme";
import { useComparisonLayout } from "@/hooks/useComparisonLayout";
import { Button } from "@/components/ui/button";
import { SourceOperationDialog } from "./SourceOperationDialog";

interface ConflictInfo {
	current_content: string;
	incoming_content: string;
	current_etag: string;
	message: string;
}
interface ConflictDiffViewProps {
	conflict: ConflictInfo;
	filePath: string;
	onResolve: (choice: "current" | "incoming") => Promise<void>;
}
export function ConflictDiffView({
	conflict,
	filePath,
	onResolve,
}: ConflictDiffViewProps) {
	const appearance = useBifrostMonacoTheme();
	const { containerRef, wide } = useComparisonLayout();
	const [choice, setChoice] = useState<"current" | "incoming" | null>(null);
	const triggerRef = useRef<HTMLButtonElement | null>(null);
	return (
		<section
			aria-label="Save conflict comparison"
			ref={containerRef}
			className="flex h-full min-h-0 min-w-0 flex-col bg-background"
		>
			<header className="shrink-0 space-y-2 border-b p-3">
				<h3 className="text-sm font-semibold">Resolve save conflict</h3>
				<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
					{filePath}
				</p>
				<p className="flex items-start gap-2 text-sm">
					<AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--bf-warning)]" />
					<span className="min-w-0 [overflow-wrap:anywhere]">
						{conflict.message}
					</span>
				</p>
			</header>
			<div className="shrink-0 border-b text-xs text-muted-foreground">
				{wide ? (
					<div className="grid grid-cols-2">
						<span className="border-r px-3 py-2">
							Server version
						</span>
						<span className="px-3 py-2">Your local version</span>
					</div>
				) : (
					<p className="px-3 py-2">
						Server → Local · Unified comparison
					</p>
				)}
			</div>
			<div className="min-h-0 min-w-0 flex-1">
				<DiffEditor
					height="100%"
					language={
						filePath.endsWith(".py")
							? "python"
							: filePath.endsWith(".json")
								? "json"
								: "plaintext"
					}
					theme={appearance.theme}
					beforeMount={appearance.beforeMount}
					onMount={appearance.onMount}
					original={conflict.current_content}
					modified={conflict.incoming_content}
					options={{
						...appearance.options,
						readOnly: true,
						minimap: { enabled: false },
						scrollBeyondLastLine: false,
						renderSideBySide: wide,
						wordWrap: "on",
						diffWordWrap: "on",
						lineNumbersMinChars: 3,
					}}
				/>
			</div>
			<footer className="flex shrink-0 flex-wrap gap-2 border-t p-3">
				<Button
					type="button"
					variant="outline"
					className="min-h-11 h-auto whitespace-normal"
					onClick={(event) => {
						triggerRef.current = event.currentTarget;
						setChoice("current");
					}}
				>
					Use server version
				</Button>
				<Button
					type="button"
					variant="outline"
					className="min-h-11 h-auto whitespace-normal"
					onClick={(event) => {
						triggerRef.current = event.currentTarget;
						setChoice("incoming");
					}}
				>
					Use local version
				</Button>
			</footer>
			{choice && (
				<SourceOperationDialog
					title={
						choice === "current"
							? "Use server version?"
							: "Use local version?"
					}
					description={
						choice === "current"
							? "Replace your local edits with the server version shown in this comparison."
							: "Overwrite the server file with the local version shown in this comparison."
					}
					confirmLabel={
						choice === "current"
							? "Use server version"
							: "Use local version"
					}
					pendingLabel="Resolving conflict…"
					cancelLabel="Keep reviewing"
					onConfirm={() => onResolve(choice)}
					onClose={() => setChoice(null)}
					onRestoreFocus={() => triggerRef.current?.focus()}
				>
					<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
						{filePath}
					</p>
				</SourceOperationDialog>
			)}
		</section>
	);
}
