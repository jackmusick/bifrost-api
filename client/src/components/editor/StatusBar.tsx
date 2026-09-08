import { useEditorStore } from "@/stores/editorStore";
import { useWorkflowsStore } from "@/stores/workflowsStore";
import { useUploadProgress, useUploadStore } from "@/stores/uploadStore";
import { useFileActivityStore } from "@/stores/fileActivityStore";
import { Radio } from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import { EditorFileStatus } from "./EditorFileStatus";
import { EditorUploadStatus } from "./EditorUploadStatus";

/**
 * Status bar showing file info, cursor position, and save status
 */
export function StatusBar() {
	const tabs = useEditorStore((state) => state.tabs);
	const activeTabIndex = useEditorStore((state) => state.activeTabIndex);
	const {
		state: uploadState,
		resetState: resetUpload,
		cancelUpload,
	} = useUploadProgress();
	const isUploadCancelled = useUploadStore((state) => state.isCancelled);
	const activeWatchers = useFileActivityStore((s) => s.activeWatchers);
	const recentPushes = useFileActivityStore((s) => s.recentPushes);

	// Tick every 30s to re-evaluate recency filtering
	const [now, setNow] = useState(() => Date.now());
	useEffect(() => {
		const timer = setInterval(() => setNow(Date.now()), 30_000);
		return () => clearInterval(timer);
	}, []);

	// Most recent push in last 2 minutes
	const latestPush = useMemo(() => {
		const filtered = recentPushes.filter(
			(p) => now - new Date(p.timestamp).getTime() < 120_000,
		);
		return filtered.length > 0 ? filtered[filtered.length - 1] : undefined;
	}, [recentPushes, now]);

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
	const isWorkflow = useWorkflowsStore((state) =>
		openFile?.type === "file"
			? state.workflowsByPath.has(openFile.path)
			: false,
	);

	// Check if we should show upload state
	const showUploadProgress =
		uploadState.isUploading || uploadState.totalCount > 0;

	return (
		<div className="flex flex-col gap-1 border-t bg-muted/50 px-3 py-1.5 text-[11px] text-muted-foreground sm:min-h-6 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-0 sm:text-xs">
			<div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:gap-4">
				{/* Upload progress - takes priority when active */}
				{showUploadProgress ? (
					<EditorUploadStatus
						state={{
							...uploadState,
							isCancelled: isUploadCancelled,
						}}
						onCancel={cancelUpload}
						onDismiss={resetUpload}
					/>
				) : openFile ? (
					<EditorFileStatus
						path={openFile.path}
						isWorkflow={isWorkflow}
						saveState={saveState}
						language={selectedLanguage}
						cursor={cursorPosition}
					/>
				) : null}
			</div>

			<div className="flex min-w-0 flex-wrap items-center gap-2 text-xs empty:hidden sm:max-w-sm">
				{/* CLI Watch Activity */}
				{activeWatchers.length > 0 && (
					<span className="flex items-center gap-1 text-[var(--bf-success)]">
						<Radio className="h-3 w-3 animate-pulse motion-reduce:animate-none!" />
						{activeWatchers.length === 1
							? `CLI watch (${activeWatchers[0].user_name})`
							: `${activeWatchers.length} CLI watchers`}
					</span>
				)}
				{!activeWatchers.length && latestPush && (
					<span className="flex min-w-0 items-center gap-1 text-muted-foreground [overflow-wrap:anywhere]">
						{latestPush.user_name} pushed {latestPush.file_count}{" "}
						files to {latestPush.prefix}
					</span>
				)}
			</div>
		</div>
	);
}
