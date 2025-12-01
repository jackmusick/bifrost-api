import { useEditorStore } from "@/stores/editorStore";
import { useWorkflowsStore } from "@/stores/workflowsStore";
import { Circle, Workflow } from "lucide-react";
import { useMemo } from "react";

/**
 * Status bar showing file info, cursor position, and save status
 */
export function StatusBar() {
	const tabs = useEditorStore((state) => state.tabs);
	const activeTabIndex = useEditorStore((state) => state.activeTabIndex);
	const isWorkflowFile = useWorkflowsStore((state) => state.isWorkflowFile);

	// Compute active tab from state
	const activeTab =
		activeTabIndex >= 0 && activeTabIndex < tabs.length
			? tabs[activeTabIndex]
			: null;

	const openFile = activeTab?.file || null;
	const cursorPosition = activeTab?.cursorPosition || { line: 1, column: 1 };
	const saveState = activeTab?.saveState || "clean";
	const selectedLanguage = activeTab?.selectedLanguage || "";

	// Check if current file is a workflow
	const isWorkflow = useMemo(() => {
		if (!openFile || openFile.type !== "file") return false;
		return isWorkflowFile(openFile.path);
	}, [openFile, isWorkflowFile]);

	// Get save status text
	const getSaveStatusText = () => {
		switch (saveState) {
			case "saving":
				return "Saving...";
			case "saved":
				return `Saved at ${new Date().toLocaleTimeString()}`;
			case "conflict":
				return "Conflict with server version";
			case "dirty":
				return "Unsaved changes";
			default:
				return null;
		}
	};

	const saveStatusText = getSaveStatusText();

	return (
		<div className="flex h-6 items-center justify-between border-t bg-muted/50 px-4 text-xs text-muted-foreground">
			<div className="flex items-center gap-4">
				{/* File path */}
				{openFile && <span className="font-mono">{openFile.path}</span>}

				{/* File type badge */}
				{openFile && openFile.path.endsWith(".py") && (
					<span
						className={`flex items-center gap-1 rounded px-2 py-0.5 font-medium ${
							isWorkflow
								? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
								: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
						}`}
					>
						{isWorkflow && <Workflow className="h-3 w-3" />}
						{isWorkflow ? "Workflow" : "Python Script"}
					</span>
				)}

				{/* Save status */}
				{saveStatusText && (
					<span
						className={`flex items-center gap-1 ${
							saveState === "conflict"
								? "text-orange-600"
								: saveState === "saved"
									? "text-green-600"
									: saveState === "saving"
										? "text-blue-600"
										: "text-amber-600"
						}`}
					>
						<Circle className="h-2 w-2 fill-current" />
						{saveStatusText}
					</span>
				)}
			</div>

			<div className="flex items-center gap-4">
				{/* Language */}
				{selectedLanguage && (
					<span className="capitalize">{selectedLanguage}</span>
				)}

				{/* Cursor position */}
				{openFile && (
					<span>
						Ln {cursorPosition.line}, Col {cursorPosition.column}
					</span>
				)}
			</div>
		</div>
	);
}
