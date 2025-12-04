import { useEffect, useCallback } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { useSaveQueue } from "./useSaveQueue";
import { fileService, FileConflictError } from "@/services/fileService";
import type { ConflictReason } from "@/stores/editorStore";
import { sdkScannerService } from "@/services/sdkScannerService";
import { useReloadWorkflowFile } from "./useWorkflows";

/**
 * Auto-save hook with 1-second debounce and save queue.
 * Ensures saves complete even when switching tabs (VS Code-like behavior).
 */
export function useAutoSave() {
	// Subscribe to tabs and activeTabIndex directly (not getters!)
	const tabs = useEditorStore((state) => state.tabs);
	const activeTabIndex = useEditorStore((state) => state.activeTabIndex);
	const setSaveState = useEditorStore((state) => state.setSaveState);
	const setConflictState = useEditorStore((state) => state.setConflictState);

	// Compute active tab values from subscribed state
	const activeTab =
		activeTabIndex >= 0 && activeTabIndex < tabs.length
			? tabs[activeTabIndex]
			: null;

	const openFile = activeTab?.file || null;
	const fileContent = activeTab?.content || "";
	const unsavedChanges = activeTab?.unsavedChanges || false;
	const encoding = activeTab?.encoding || "utf-8";
	const currentEtag = activeTab?.etag;
	const saveState = activeTab?.saveState;

	const { enqueueSave } = useSaveQueue();
	const { mutate: reloadWorkflowFile } = useReloadWorkflowFile();

	// Auto-save with 1-second debounce using save queue
	useEffect(() => {
		// Only enqueue if we have unsaved changes and not in conflict
		if (!unsavedChanges || !openFile || saveState === "conflict") {
			return;
		}

		// Set dirty state immediately (prevent infinite loop by checking current state)
		if (saveState !== "dirty") {
			setSaveState(activeTabIndex, "dirty");
		}

		// Update save state to saving after 950ms (visual feedback before save)
		const savingTimer = setTimeout(() => {
			setSaveState(activeTabIndex, "saving");
		}, 950);

		// Enqueue save with completion and conflict callbacks
		enqueueSave(
			openFile.path,
			fileContent,
			encoding,
			currentEtag,
			(newEtag) => {
				// This runs when save actually completes
				// Update the tab with the new etag
				const state = useEditorStore.getState();
				const newTabs = [...state.tabs];
				if (newTabs[activeTabIndex]) {
					newTabs[activeTabIndex] = {
						...newTabs[activeTabIndex]!,
						etag: newEtag,
						unsavedChanges: false,
						saveState: "saved",
					};
					useEditorStore.setState({ tabs: newTabs });
				}

				// Show green cloud for 2.5 seconds
				setTimeout(() => {
					setSaveState(activeTabIndex, "clean");
				}, 2500);

				// Run post-save tasks for Python workflow files
				if (openFile && openFile.name.endsWith(".py")) {
					// Scan for SDK usage issues (missing configs, secrets, OAuth)
					sdkScannerService.scanFileAndNotify(
						openFile.path,
						fileContent,
					);
					// Incrementally reload workflows for this file
					// This updates the workflows store to reflect workflow changes
					reloadWorkflowFile();
				}
			},
			(reason) => {
				// This runs when a conflict is detected
				setConflictState(activeTabIndex, reason);
			},
		);

		return () => clearTimeout(savingTimer);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [
		unsavedChanges,
		openFile,
		fileContent,
		encoding,
		currentEtag,
		activeTabIndex,
		enqueueSave,
		setSaveState,
		setConflictState,
	]);

	// Manual save function (for Cmd+S)
	const manualSave = useCallback(async () => {
		if (!openFile || !unsavedChanges) {
			return;
		}

		// Force immediate save (bypasses debounce)
		setSaveState(activeTabIndex, "saving");

		try {
			const response = await fileService.writeFile(
				openFile.path,
				fileContent,
				encoding,
				currentEtag,
			);

			// Update tab with new etag
			const state = useEditorStore.getState();
			const newTabs = [...state.tabs];
			if (newTabs[activeTabIndex]) {
				newTabs[activeTabIndex] = {
					...newTabs[activeTabIndex]!,
					etag: response.etag,
					unsavedChanges: false,
					saveState: "saved",
				};
				useEditorStore.setState({ tabs: newTabs });
			}

			// Show green cloud briefly
			setTimeout(() => {
				setSaveState(activeTabIndex, "clean");
			}, 2500);

			// Run post-save tasks for Python workflow files
			if (openFile.name.endsWith(".py")) {
				// Scan for SDK usage issues (missing configs, secrets, OAuth)
				sdkScannerService.scanFileAndNotify(openFile.path, fileContent);
			}
		} catch (error) {
			if (error instanceof FileConflictError) {
				// Show conflict state
				setConflictState(
					activeTabIndex,
					error.conflictData.reason as ConflictReason,
				);
			} else {
				console.error("Failed to save:", error);
				setSaveState(activeTabIndex, "dirty");
			}
		}
	}, [
		openFile,
		fileContent,
		encoding,
		currentEtag,
		unsavedChanges,
		activeTabIndex,
		setSaveState,
		setConflictState,
	]);

	return { manualSave };
}
