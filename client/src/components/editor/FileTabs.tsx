import { UnsavedTabsDialog } from "./UnsavedTabsDialog";
import { X, Cloud, Loader2, CloudCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { useEditorSession } from "@/hooks/useEditorSession";
import { fileService } from "@/services/fileService";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuSeparator,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
	draggable,
	dropTargetForElements,
} from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { FileTabConflictMenu } from "@/components/editor/FileTabConflictMenu";

/**
 * File tabs component
 * Horizontally scrollable tabs for open files with drag-and-drop reordering
 * Each tab shows file name, unsaved indicator, and close button
 * Right-click for context menu: Close, Close Others, Close All
 */
export function FileTabs({ onEmpty }: { onEmpty?: () => void }) {
	const {
		tabs,
		activeTabIndex,
		setActiveTab,
		closeTab,
		openFileInTab,
		setLoadingFile,
		reorderTabs,
		setConflictState,
	} = useEditorSession();

	const tabsRef = useRef<HTMLDivElement>(null);
	const closeOriginRef = useRef<HTMLElement | null>(null);
	const [pendingClosePaths, setPendingClosePaths] = useState<string[]>([]);
	const focusActiveTab = () => {
		const activeButton = tabsRef.current?.querySelector<HTMLButtonElement>(
			'button[aria-pressed="true"]',
		);
		if (activeButton) activeButton.focus();
		else onEmpty?.();
	};
	const closePaths = (paths: string[]) => {
		// Resolve current indices so tab reordering cannot close a different file.
		tabs.map((tab, index) => (paths.includes(tab.file.path) ? index : -1))
			.filter((index) => index >= 0)
			.reverse()
			.forEach((index) => closeTab(index));
		requestAnimationFrame(focusActiveTab);
	};
	const requestClose = (paths: string[], origin?: HTMLElement | null) => {
		closeOriginRef.current =
			origin ??
			(document.activeElement instanceof HTMLElement
				? document.activeElement
				: null);
		if (
			tabs.some(
				(tab) => paths.includes(tab.file.path) && tab.unsavedChanges,
			)
		)
			setPendingClosePaths(paths);
		else closePaths(paths);
	};

	// Handle tab click - only load from server if content is empty
	const handleTabClick = async (index: number) => {
		if (index === activeTabIndex) return; // Already active

		const tab = tabs[index];
		if (!tab) return;

		// If content already loaded, check for conflicts before switching
		// Skip conflict check during indexing (server modifies file, creating etag mismatch)
		if (
			tab.content !== "" &&
			tab.etag &&
			!useEditorStore.getState().isIndexing
		) {
			try {
				const serverFile = await fileService.readFile(tab.file.path);

				// Check if server content changed
				if (serverFile.etag !== tab.etag) {
					// If there are no unsaved changes, just accept the server version silently
					if (!tab.unsavedChanges) {
						const newTabs = [...tabs];
						newTabs[index] = {
							...tab,
							content: serverFile.content,
							etag: serverFile.etag,
							encoding: serverFile.encoding as "utf-8" | "base64",
						};
						useEditorStore.setState({ tabs: newTabs });
					} else {
						// Only show conflict if we have unsaved local changes
						setConflictState(index, "content_changed");
					}
				}
			} catch (error: unknown) {
				// Check if file was deleted (404)
				if (error instanceof Error && error.message.includes("404")) {
					setConflictState(index, "path_not_found");
				}
				// Ignore other errors (network issues, etc.)
			}

			// Switch to tab
			setActiveTab(index);
			return;
		}

		// Otherwise, load from server (first time opening)
		try {
			setLoadingFile(true);
			const response = await fileService.readFile(tab.file.path);
			openFileInTab(
				tab.file,
				response.content,
				response.encoding as "utf-8" | "base64",
				response.etag,
			);
		} catch {
			toast.error("Failed to load file");
			setLoadingFile(false);
			// Still switch to the tab even if loading fails
			setActiveTab(index);
		}
	};

	if (tabs.length === 0) {
		return null;
	}

	return (
		<div
			className="flex min-h-11 items-stretch overflow-x-auto border-b bg-muted/30"
			ref={tabsRef}
			aria-label="Open files"
			role="group"
		>
			<div className="flex min-w-full">
				{tabs.map((tab, index) => (
					<FileTab
						key={tab.file.path}
						tab={tab}
						index={index}
						isActive={index === activeTabIndex}
						onTabClick={() => handleTabClick(index)}
						onClose={(origin) =>
							requestClose([tab.file.path], origin)
						}
						onCloseOthers={() =>
							requestClose(
								tabs
									.filter(
										(other) =>
											other.file.path !== tab.file.path,
									)
									.map((other) => other.file.path),
							)
						}
						onCloseAll={() =>
							requestClose(tabs.map((other) => other.file.path))
						}
						onReorder={reorderTabs}
					/>
				))}
			</div>
			<UnsavedTabsDialog
				isSaving={tabs.some(
					(tab) =>
						pendingClosePaths.includes(tab.file.path) &&
						tab.saveState === "saving",
				)}
				onReturnFocus={() => {
					const origin = closeOriginRef.current;
					if (
						origin?.isConnected &&
						tabsRef.current?.contains(origin)
					)
						origin.focus();
					else focusActiveTab();
				}}
				open={pendingClosePaths.length > 0}
				paths={tabs
					.filter(
						(tab) =>
							pendingClosePaths.includes(tab.file.path) &&
							tab.unsavedChanges,
					)
					.map((tab) => tab.file.path)}
				onOpenChange={(open) => {
					if (!open) setPendingClosePaths([]);
				}}
				onDiscard={() => {
					closePaths(pendingClosePaths);
					setPendingClosePaths([]);
				}}
			/>
		</div>
	);
}

interface FileTabProps {
	tab: {
		file: { name: string; path: string };
		unsavedChanges: boolean;
		saveState?: "clean" | "dirty" | "saving" | "saved" | "conflict";
		conflictReason?:
			"content_changed" | "path_not_found" | "workflows_would_deactivate";
		serverContentDiffers?: boolean;
	};
	index: number;
	isActive: boolean;
	onTabClick: () => void;
	onClose: (origin?: HTMLElement | null) => void;
	onCloseOthers: () => void;
	onCloseAll: () => void;
	onReorder: (fromIndex: number, toIndex: number) => void;
}

function FileTab({
	tab,
	index,
	isActive,
	onTabClick,
	onClose,
	onCloseOthers,
	onCloseAll,
	onReorder,
}: FileTabProps) {
	const resolveConflict = useEditorStore((state) => state.resolveConflict);
	const tabRef = useRef<HTMLDivElement>(null);
	const [isDragging, setIsDragging] = useState(false);
	const [isDropTarget, setIsDropTarget] = useState(false);

	useEffect(() => {
		const element = tabRef.current;
		if (!element) return;

		return combine(
			draggable({
				element,
				getInitialData: () => ({ index, type: "file-tab" }),
				onDragStart: () => setIsDragging(true),
				onDrop: () => setIsDragging(false),
			}),
			dropTargetForElements({
				element,
				getData: () => ({ index, type: "file-tab" }),
				canDrop: ({ source }) => {
					return (
						source.data["type"] === "file-tab" &&
						source.data["index"] !== index
					);
				},
				onDragEnter: () => setIsDropTarget(true),
				onDragLeave: () => setIsDropTarget(false),
				onDrop: ({ source }) => {
					setIsDropTarget(false);
					const sourceIndex = source.data["index"];
					if (
						typeof sourceIndex === "number" &&
						sourceIndex !== index
					) {
						onReorder(sourceIndex, index);
					}
				},
			}),
		);
	}, [index, onReorder]);

	return (
		<ContextMenu>
			<ContextMenuTrigger asChild>
				<div
					ref={tabRef}
					className={cn(
						"group flex min-w-[160px] max-w-[280px] shrink-0 items-center border-r text-sm transition-colors motion-reduce:transition-none",
						isActive
							? "bg-background text-foreground"
							: "bg-muted/30 text-muted-foreground hover:bg-muted/50",
						isDragging && "opacity-50",
						isDropTarget &&
							"bg-primary/20 border-l-2 border-l-primary",
					)}
				>
					{tab.saveState === "conflict" && tab.conflictReason && (
						<FileTabConflictMenu
							fileName={tab.file.name}
							conflictReason={tab.conflictReason}
							onResolve={(action) => {
								if (action === "close")
									onClose(
										tabRef.current?.querySelector<HTMLButtonElement>(
											"button",
										),
									);
								else resolveConflict(index, action);
							}}
						/>
					)}
					<button
						type="button"
						onClick={onTabClick}
						aria-pressed={isActive}
						aria-label={`Open ${tab.file.path}`}
						title={tab.file.path}
						className="flex min-h-11 min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
					>
						{tab.saveState === "saving" ? (
							<Loader2 className="size-3.5 shrink-0 animate-spin text-primary motion-reduce:animate-none!" />
						) : tab.saveState === "saved" ? (
							<CloudCheck className="size-3.5 shrink-0 text-[var(--bf-success)]" />
						) : (
							<Cloud
								className={cn(
									"size-3.5 shrink-0",
									tab.unsavedChanges
										? "text-primary"
										: "text-muted-foreground",
								)}
							/>
						)}
						<span className="min-w-0 [overflow-wrap:anywhere]">
							{tab.file.name}
						</span>
						{tab.unsavedChanges && (
							<span className="sr-only">Unsaved changes</span>
						)}
					</button>

					{/* Close button - always visible */}
					<button
						onClick={(e) => {
							e.stopPropagation();
							onClose();
						}}
						type="button"
						className="flex size-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] hover:bg-muted-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
						title="Close"
						aria-label={`Close ${tab.file.name}`}
					>
						<X className="h-3 w-3" />
					</button>
				</div>
			</ContextMenuTrigger>
			<ContextMenuContent>
				<ContextMenuItem onClick={() => onClose()}>
					Close
				</ContextMenuItem>
				<ContextMenuItem onClick={onCloseOthers}>
					Close Others
				</ContextMenuItem>
				<ContextMenuSeparator />
				<ContextMenuItem onClick={onCloseAll}>
					Close All
				</ContextMenuItem>
			</ContextMenuContent>
		</ContextMenu>
	);
}
