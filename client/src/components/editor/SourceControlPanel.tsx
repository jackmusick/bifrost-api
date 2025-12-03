import { useState, useEffect, useRef, useCallback } from "react";
import {
	GitBranch,
	AlertCircle,
	Check,
	Loader2,
	RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
	githubService,
	type FileChange,
	type GitStatusResponse,
} from "@/services/github";
import { useEditorStore } from "@/stores/editorStore";
import { fileService } from "@/services/fileService";
import { ChangesList } from "./ChangesList";

/**
 * Source Control panel for Git/GitHub integration
 *
 * NOTE: This is a stub UI matching the backend GitHub router stub.
 * Full Git integration features are not yet implemented in the Docker deployment.
 * Shows basic status and provides placeholders for commit/push operations.
 */
export function SourceControlPanel() {
	const [status, setStatus] = useState<GitStatusResponse | null>(null);
	const [commitMessage, setCommitMessage] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [isCommitting, setIsCommitting] = useState(false);

	// Use ref to track loading state synchronously (prevents React 18 double-call race condition)
	const isLoadingRef = useRef(false);

	const openFileInTab = useEditorStore((state) => state.openFileInTab);
	const sidebarPanel = useEditorStore((state) => state.sidebarPanel);

	const refreshStatus = useCallback(async () => {
		// Prevent duplicate fetches using ref (synchronous check)
		if (isLoadingRef.current) {
			return;
		}

		isLoadingRef.current = true;
		setIsLoading(true);
		try {
			const result = await githubService.getStatus();
			setStatus(result);

			// Also check for changes (will return empty for stub)
			await githubService.getChanges();
			// Store changes for display (currently always empty in stub)
		} catch (error) {
			console.error("Failed to refresh Git status:", error);
			toast.error("Failed to refresh Git status");
		} finally {
			isLoadingRef.current = false;
			setIsLoading(false);
		}
	}, []);

	// Load status when this tab becomes active
	useEffect(() => {
		// Only refresh if source control panel is active
		if (sidebarPanel !== "sourceControl") {
			return;
		}

		// Initial load when panel becomes active
		refreshStatus();

		// Set up event listeners for visibility and git status changes
		const handleVisibilityChange = () => {
			if (!document.hidden && sidebarPanel === "sourceControl") {
				refreshStatus();
			}
		};

		const handleGitStatusChanged = () => {
			if (sidebarPanel === "sourceControl") {
				refreshStatus();
			}
		};

		document.addEventListener("visibilitychange", handleVisibilityChange);
		window.addEventListener("git-status-changed", handleGitStatusChanged);

		return () => {
			document.removeEventListener(
				"visibilitychange",
				handleVisibilityChange,
			);
			window.removeEventListener(
				"git-status-changed",
				handleGitStatusChanged,
			);
		};
	}, [sidebarPanel, refreshStatus]);

	const handleCommit = async () => {
		if (!commitMessage.trim()) {
			toast.error("Please enter a commit message");
			return;
		}

		setIsCommitting(true);
		try {
			// This will fail with 501 Not Implemented
			await githubService.commit(commitMessage);

			toast.success("Changes committed");
			setCommitMessage("");
			await refreshStatus();
		} catch (error) {
			console.error("Failed to commit:", error);
			if (error instanceof Error && error.message.includes("not yet implemented")) {
				toast.error("Git integration not yet available", {
					description: "This feature will be available in a future update",
				});
			} else {
				toast.error("Failed to commit");
			}
		} finally {
			setIsCommitting(false);
		}
	};

	const handleFileClick = async (file: FileChange) => {
		try {
			// Load file content from workspace
			const fileData = await fileService.readFile(file.path);

			// Construct FileMetadata from response
			const fileName = fileData.path.split("/").pop() || "";
			const fileMetadata = {
				path: fileData.path,
				name: fileName,
				size: fileData.size,
				type: "file" as const,
				extension: fileName.includes(".")
					? fileName.split(".").pop() || null
					: null,
				modified: fileData.modified,
				isReadOnly: false,
			};

			// Open in editor tab
			openFileInTab(
				fileMetadata,
				fileData.content,
				fileData.encoding as "utf-8" | "base64",
				fileData.etag,
			);
		} catch (error) {
			console.error("Failed to open file:", error);
			toast.error(`Failed to open ${file.path}`);
		}
	};

	// Show loading state while fetching initial status
	if (isLoading && !status) {
		return (
			<div className="flex h-full flex-col p-4">
				<div className="flex items-center gap-2 mb-4">
					<GitBranch className="h-5 w-5" />
					<h3 className="text-sm font-semibold">Source Control</h3>
				</div>

				<div className="flex flex-col items-center justify-center flex-1 text-center">
					<Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
					<p className="text-sm text-muted-foreground">
						Loading Git status...
					</p>
				</div>
			</div>
		);
	}

	if (!status?.isGitRepo) {
		return (
			<div className="flex h-full flex-col p-4">
				<div className="flex items-center gap-2 mb-4">
					<GitBranch className="h-5 w-5" />
					<h3 className="text-sm font-semibold">Source Control</h3>
				</div>

				<div className="flex flex-col items-center justify-center flex-1 text-center">
					<GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
					<p className="text-sm text-muted-foreground mb-2">
						Git not initialized
					</p>
					<p className="text-xs text-muted-foreground">
						Configure GitHub integration in Settings
					</p>
					<div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
						<div className="flex items-center gap-2 mb-2">
							<AlertCircle className="h-4 w-4 text-amber-600" />
							<p className="text-xs font-medium text-amber-700 dark:text-amber-400">
								Git integration not yet available
							</p>
						</div>
						<p className="text-xs text-amber-600/80 dark:text-amber-400/80">
							This feature will be implemented in a future update
						</p>
					</div>
				</div>
			</div>
		);
	}

	const hasChanges = (status.changedFiles ?? 0) > 0;

	return (
		<div className="flex h-full flex-col">
			{/* Header */}
			<div className="flex items-center justify-between p-4 border-b">
				<div className="flex items-center gap-2">
					<GitBranch className="h-5 w-5" />
					<div className="flex flex-col">
						<h3 className="text-sm font-semibold">
							Source Control
						</h3>
						{status.currentBranch && (
							<span className="text-xs text-muted-foreground">
								{status.currentBranch}
							</span>
						)}
					</div>
				</div>
				<button
					onClick={refreshStatus}
					disabled={isLoading}
					className="p-1.5 rounded hover:bg-muted/50 transition-colors disabled:opacity-50"
					title="Refresh status"
				>
					{isLoading ? (
						<Loader2 className="h-4 w-4 animate-spin" />
					) : (
						<RefreshCw className="h-4 w-4" />
					)}
				</button>
			</div>

			{/* Status info */}
			<div className="px-4 py-3 border-b space-y-1 text-xs text-muted-foreground">
				<div>Changes: {status.changedFiles} file(s)</div>
				<div>Commits ahead: {status.commitsAhead}</div>
				<div>Commits behind: {status.commitsBehind}</div>
			</div>

			{/* Commit section */}
			{hasChanges && (
				<div className="px-4 py-3 border-b space-y-2">
					<Input
						id="commit-message"
						placeholder={`Message (#Enter to commit on "${status.currentBranch || "main"}")`}
						value={commitMessage}
						onChange={(e) => setCommitMessage(e.target.value)}
						onKeyDown={(e) => {
							if (e.key === "Enter" && !e.shiftKey) {
								e.preventDefault();
								handleCommit();
							}
						}}
						className="text-sm"
					/>
					<Button
						size="sm"
						className="w-full"
						onClick={handleCommit}
						disabled={
							!commitMessage.trim() ||
							isCommitting ||
							isLoading
						}
					>
						{isCommitting ? (
							<Loader2 className="h-4 w-4 mr-2 animate-spin" />
						) : (
							<Check className="h-4 w-4 mr-2" />
						)}
						Commit
					</Button>
				</div>
			)}

			{/* Changes section */}
			<div className="flex-1 flex flex-col min-h-0">
				<ChangesList
					changes={[]} // Stub always returns empty
					hasConflicts={false}
					onFileClick={handleFileClick}
					isLoading={false}
				/>
			</div>
		</div>
	);
}
