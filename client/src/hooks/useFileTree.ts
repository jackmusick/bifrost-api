import { useState, useCallback } from "react";
import { fileService, type FileMetadata } from "@/services/fileService";

export interface FileTreeNode extends FileMetadata {
	children?: FileTreeNode[];
	level: number;
}

interface FileTreeState {
	fileMap: Map<string, FileMetadata[]>; // path -> children mapping
	expandedFolders: Set<string>;
	isLoading: boolean;
}

/**
 * File tree state management hook
 * Handles loading files, expand/collapse state, and hierarchical tree structure
 */
export function useFileTree() {
	const [state, setState] = useState<FileTreeState>({
		fileMap: new Map([["", []]]), // Initialize with root
		expandedFolders: new Set<string>(),
		isLoading: false,
	});

	const sortFiles = (files: FileMetadata[]): FileMetadata[] => {
		return [...files].sort((a, b) => {
			// Folders first
			if (a.type === "folder" && b.type !== "folder") return -1;
			if (a.type !== "folder" && b.type === "folder") return 1;

			// Then alphabetically (case-insensitive)
			return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
		});
	};

	const loadFiles = useCallback(async (path: string = "") => {
		setState((prev) => ({ ...prev, isLoading: true }));

		try {
			const files = await fileService.listFiles(path);
			const sortedFiles = sortFiles(files);
			setState((prev) => {
				const newFileMap = new Map(prev.fileMap);
				newFileMap.set(path, sortedFiles);
				return {
					...prev,
					fileMap: newFileMap,
					isLoading: false,
				};
			});
		} catch {
			setState((prev) => ({ ...prev, isLoading: false }));
		}
	}, []);

	const toggleFolder = useCallback(
		async (folderPath: string) => {
			setState((prev) => {
				const newExpandedFolders = new Set(prev.expandedFolders);
				const wasExpanded = newExpandedFolders.has(folderPath);

				if (wasExpanded) {
					newExpandedFolders.delete(folderPath);
				} else {
					newExpandedFolders.add(folderPath);
				}

				return {
					...prev,
					expandedFolders: newExpandedFolders,
				};
			});

			// Load folder contents if not already loaded and expanding
			if (
				!state.expandedFolders.has(folderPath) &&
				!state.fileMap.has(folderPath)
			) {
				await loadFiles(folderPath);
			}
		},
		[state.expandedFolders, state.fileMap, loadFiles],
	);

	const isFolderExpanded = useCallback(
		(folderPath: string) => {
			return state.expandedFolders.has(folderPath);
		},
		[state.expandedFolders],
	);

	const refreshAll = useCallback(async () => {
		// Reload root
		await loadFiles("");

		// Reload all expanded folders
		const expandedFoldersList = Array.from(state.expandedFolders);
		for (const folderPath of expandedFoldersList) {
			await loadFiles(folderPath);
		}
	}, [state.expandedFolders, loadFiles]);

	// Build flat list of visible files with proper hierarchy
	const buildVisibleFiles = useCallback((): FileTreeNode[] => {
		const result: FileTreeNode[] = [];

		const addFilesRecursively = (path: string, level: number) => {
			const files = state.fileMap.get(path) || [];

			for (const file of files) {
				const node: FileTreeNode = { ...file, level };
				result.push(node);

				// If it's a folder and it's expanded, add its children
				if (
					file.type === "folder" &&
					state.expandedFolders.has(file.path)
				) {
					addFilesRecursively(file.path, level + 1);
				}
			}
		};

		addFilesRecursively("", 0);
		return result;
	}, [state.fileMap, state.expandedFolders]);

	return {
		files: buildVisibleFiles(),
		isLoading: state.isLoading,
		loadFiles,
		toggleFolder,
		isFolderExpanded,
		refreshAll,
	};
}
