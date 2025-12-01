import { useState, useCallback, useRef } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { fileService } from "@/services/fileService";
import type { FileMetadata } from "@/services/fileService";

/**
 * Hook that provides a centralized file loading function with conflict detection
 *
 * This ensures that all file loads (from tree, tabs, or focus events) follow
 * the same conflict resolution logic:
 * - If file has no unsaved changes → reload silently
 * - If file has unsaved changes → show conflict dialog
 */
export function useFileLoader() {
	const activeTab = useEditorStore((state) => state.activeTab);
	const openFileInTab = useEditorStore((state) => state.openFileInTab);
	const setLoadingFile = useEditorStore((state) => state.setLoadingFile);

	const [conflictState, setConflictState] = useState<{
		file: FileMetadata;
		newContent: string;
		newEncoding: "utf-8" | "base64";
		newEtag: string;
	} | null>(null);

	// Track if we're currently loading to prevent duplicate requests
	const isLoadingRef = useRef(false);

	/**
	 * Load a file with automatic conflict detection
	 *
	 * @param file - File metadata to load
	 * @returns Promise that resolves when file is loaded or conflict is presented
	 */
	const loadFile = useCallback(
		async (file: FileMetadata) => {
			// Prevent duplicate concurrent requests
			if (isLoadingRef.current) {
				return;
			}

			try {
				isLoadingRef.current = true;
				setLoadingFile(true);

				// Fetch file content from server
				const response = await fileService.readFile(file.path);

				// Check if this file is currently open and has changes
				const existingTab =
					activeTab?.file.path === file.path ? activeTab : null;

				if (existingTab) {
					// Compare content to see if anything actually changed
					const contentChanged =
						response.content !== existingTab.content;

					if (!contentChanged) {
						// Content is identical - no need to reload or show dialog
						return;
					}

					if (existingTab.unsavedChanges) {
						// Conflict! User has unsaved changes AND server content changed
						setConflictState({
							file,
							newContent: response.content,
							newEncoding: response.encoding as
								| "utf-8"
								| "base64",
							newEtag: response.etag || "",
						});
						return; // Don't load yet - wait for user decision
					}
				}

				// No conflict - load the file
				openFileInTab(
					file,
					response.content,
					response.encoding as "utf-8" | "base64",
					response.etag,
				);
			} catch (error) {
				console.error(
					`[FileLoader] Failed to load file ${file.path}:`,
					error,
				);
			} finally {
				isLoadingRef.current = false;
				setLoadingFile(false);
			}
		},
		[activeTab, openFileInTab, setLoadingFile],
	);

	/**
	 * Handle "Keep My Changes" - dismiss conflict dialog
	 */
	const handleKeepChanges = useCallback(() => {
		setConflictState(null);
	}, []);

	/**
	 * Handle "Discard My Changes" - load the new file version
	 */
	const handleDiscardChanges = useCallback(() => {
		if (!conflictState) return;

		openFileInTab(
			conflictState.file,
			conflictState.newContent,
			conflictState.newEncoding,
			conflictState.newEtag,
		);
		setConflictState(null);
	}, [conflictState, openFileInTab]);

	return {
		loadFile,
		conflictFile: conflictState?.file.name || null,
		handleKeepChanges,
		handleDiscardChanges,
	};
}
