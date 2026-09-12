import { useState, useRef, useCallback, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";
import { WorkspaceFileTree } from "@/components/file-tree";
import { CodeEditor } from "./CodeEditor";
import { TerminalPanel } from "./TerminalPanel";
import { RunPanel } from "./RunPanel";
import { SearchPanel } from "./SearchPanel";
import { PackagePanel } from "./PackagePanel";
import { SourceControlPanel } from "./SourceControlPanel";
import { FileTabs } from "./FileTabs";
import { useEditorSession } from "@/hooks/useEditorSession";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useCmdCtrlShortcut } from "@/contexts/KeyboardContext";
import { useUploadStore } from "@/stores/uploadStore";
import { X, Save, Minus, PanelLeftClose, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAutoSave } from "@/hooks/useAutoSave";
import { cn } from "@/lib/utils";
import { EditorCloseDialog } from "./EditorCloseDialog";
import { useEditorStore } from "@/stores/editorStore";

type MobilePane = "files" | "code" | "output";

/**
 * Main editor layout container
 * Provides structure with sidebar, editor area, terminal area, and status bar
 * State is persisted, so closing and reopening restores the previous session
 */
export function EditorLayout() {
	const {
		openFile,
		unsavedChanges,
		saveState,
		sidebarPanel,
		layoutMode,
		terminalHeight,
		closeEditor,
		minimizeEditor,
		setTerminalHeight,
		setSidebarPanel,
	} = useEditorSession();

	// Auto-save and manual save
	const { manualSave } = useAutoSave();
	const isDesktop = useMediaQuery("(min-width: 1024px)");

	// Upload state for close confirmation
	const isUploading = useUploadStore((state) => state.isUploading);
	const cancelUpload = useUploadStore((state) => state.cancelUpload);

	const tabs = useEditorStore((state) => state.tabs);
	const unsavedPaths = tabs
		.filter((tab) => tab.unsavedChanges)
		.map((tab) => tab.file.path);
	const isSaving = tabs.some((tab) => tab.saveState === "saving");
	const closeButtonRef = useRef<HTMLButtonElement>(null);

	// Close confirmation dialog state
	const [showCloseConfirm, setShowCloseConfirm] = useState(false);

	// Closing clears every tab, including drafts in inactive files.
	const handleCloseEditor = useCallback(() => {
		if (isUploading || unsavedPaths.length > 0 || isSaving) {
			setShowCloseConfirm(true);
		} else {
			closeEditor();
		}
	}, [isUploading, unsavedPaths.length, isSaving, closeEditor]);

	const [sidebarWidth, setSidebarWidth] = useState(256); // 256px = w-64
	const [sidebarVisible, setSidebarVisible] = useState(true);
	const [isResizing, setIsResizing] = useState(false);
	const [isResizingTerminal, setIsResizingTerminal] = useState(false);
	const diffPreview = useEditorStore((state) => state.diffPreview);
	const activeContentKey = diffPreview
		? `diff:${diffPreview.path}`
		: openFile
			? `file:${openFile.path}`
			: undefined;
	const hasCodeContent = !!activeContentKey;
	const [mobilePane, setMobilePane] = useState<MobilePane>(
		hasCodeContent ? "code" : "files",
	);
	const [lastContentKey, setLastContentKey] = useState(activeContentKey);
	if (lastContentKey !== activeContentKey) {
		setLastContentKey(activeContentKey);
		setMobilePane(hasCodeContent ? "code" : "files");
	}
	const sidebarRef = useRef<HTMLDivElement>(null);
	const filesButtonRef = useRef<HTMLButtonElement>(null);
	const sidebarButtonRef = useRef<HTMLButtonElement>(null);
	const editorRef = useRef<HTMLDivElement>(null);

	const showDesktopSidebar = isDesktop ? sidebarVisible : true;
	const showFilesPane = isDesktop || mobilePane === "files";
	const showCodePane = isDesktop || mobilePane === "code";
	const showOutputPane = isDesktop || mobilePane === "output";

	// Register Cmd+B to toggle sidebar
	useCmdCtrlShortcut("toggle-sidebar", "b", () => {
		if (isDesktop) {
			setSidebarVisible((prev) => !prev);
		} else {
			setMobilePane((pane) =>
				pane === "files" && hasCodeContent ? "code" : "files",
			);
		}
	});

	const executeRef = useRef<(() => void) | null>(null);

	// Listen for run-editor-file event and trigger execution
	useEffect(() => {
		const handleRunEvent = () => {
			// Switch to Run panel and keep the tool rail visible.
			setSidebarPanel("run");
			if (isDesktop) {
				setSidebarVisible(true);
			} else {
				setMobilePane("files");
			}
			// If RunPanel is already mounted, execute immediately
			if (executeRef.current) {
				executeRef.current();
			}
		};

		window.addEventListener("run-editor-file", handleRunEvent);
		return () => {
			window.removeEventListener("run-editor-file", handleRunEvent);
		};
	}, [isDesktop, setSidebarPanel]);

	const handleMouseDown = useCallback((e: React.MouseEvent) => {
		e.preventDefault();
		setIsResizing(true);
	}, []);

	const handleMouseMove = useCallback(
		(e: MouseEvent) => {
			if (!isResizing) return;

			const newWidth = e.clientX - 48; // 48px for the left sidebar
			// Constrain between 150px and 600px
			const constrainedWidth = Math.max(150, Math.min(600, newWidth));
			setSidebarWidth(constrainedWidth);
		},
		[isResizing],
	);

	const handleMouseUp = useCallback(() => {
		setIsResizing(false);
	}, []);

	// Terminal resize handlers
	const handleTerminalMouseDown = useCallback((e: React.MouseEvent) => {
		e.preventDefault();
		setIsResizingTerminal(true);
	}, []);

	const handleTerminalMouseMove = useCallback(
		(e: MouseEvent) => {
			if (!isResizingTerminal || !editorRef.current) return;

			const editorRect = editorRef.current.getBoundingClientRect();
			const newHeight = editorRect.bottom - e.clientY;
			// Constrain between 100px and 600px
			const constrainedHeight = Math.max(100, Math.min(600, newHeight));
			setTerminalHeight(constrainedHeight);
		},
		[isResizingTerminal, setTerminalHeight],
	);

	const handleTerminalMouseUp = useCallback(() => {
		setIsResizingTerminal(false);
	}, []);

	// Add/remove event listeners for resizing
	useEffect(() => {
		if (isResizing) {
			document.addEventListener("mousemove", handleMouseMove);
			document.addEventListener("mouseup", handleMouseUp);
			return () => {
				document.removeEventListener("mousemove", handleMouseMove);
				document.removeEventListener("mouseup", handleMouseUp);
			};
		}
		return undefined;
	}, [isResizing, handleMouseMove, handleMouseUp]);

	// Add/remove event listeners for terminal resizing
	useEffect(() => {
		if (isResizingTerminal) {
			document.addEventListener("mousemove", handleTerminalMouseMove);
			document.addEventListener("mouseup", handleTerminalMouseUp);
			return () => {
				document.removeEventListener(
					"mousemove",
					handleTerminalMouseMove,
				);
				document.removeEventListener("mouseup", handleTerminalMouseUp);
			};
		}
		return undefined;
	}, [isResizingTerminal, handleTerminalMouseMove, handleTerminalMouseUp]);

	// If minimized, don't render anything - the unified WindowDock handles this
	if (layoutMode === "minimized") {
		return null;
	}

	return (
		<>
			<div className="flex h-dvh w-screen flex-col overflow-hidden bg-background">
				{/* Top bar with close button */}
				<div className="flex min-h-11 items-center justify-between border-b bg-muted/30 px-3 sm:h-10">
					<div className="flex min-w-0 flex-1 items-center gap-2">
						<Button
							variant="ghost"
							size="icon"
							className="hidden size-11 lg:inline-flex lg:size-6"
							ref={sidebarButtonRef}
							aria-label={
								sidebarVisible ? "Hide sidebar" : "Show sidebar"
							}
							onClick={() => setSidebarVisible(!sidebarVisible)}
							title={`${
								sidebarVisible ? "Hide" : "Show"
							} Sidebar (Cmd+B)`}
						>
							{sidebarVisible ? (
								<PanelLeftClose className="h-4 w-4" />
							) : (
								<PanelLeft className="h-4 w-4" />
							)}
						</Button>
						<Button
							variant="ghost"
							size="icon"
							className="size-11 lg:size-6"
							aria-label="Save"
							onClick={manualSave}
							disabled={!unsavedChanges || saveState === "saving"}
							title="Save (Cmd+S)"
						>
							<Save className="h-4 w-4" />
						</Button>
						{openFile && (
							<span
								className="min-w-0 truncate text-sm font-medium"
								title={openFile.path}
							>
								{openFile.path}
							</span>
						)}
					</div>
					<div className="flex shrink-0 gap-1">
						<Button
							variant="ghost"
							size="icon"
							className="size-11 lg:size-6"
							aria-label="Minimize editor"
							onClick={minimizeEditor}
							title="Minimize"
						>
							<Minus className="h-3 w-3" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							className="size-11 lg:size-6"
							ref={closeButtonRef}
							aria-label="Close editor"
							onClick={handleCloseEditor}
							title="Close"
						>
							<X className="h-3 w-3" />
						</Button>
					</div>
				</div>

				{/* Mobile mode switcher */}
				<div className="grid grid-cols-3 gap-2 border-b bg-background px-3 py-2 lg:hidden">
					<Button
						variant={
							mobilePane === "files" ? "secondary" : "outline"
						}
						className="h-11 justify-center rounded-[var(--bf-radius-control)] px-3 text-xs font-medium motion-reduce:transition-none"
						ref={filesButtonRef}
						aria-pressed={mobilePane === "files"}
						onClick={() => setMobilePane("files")}
					>
						Files &amp; Tools
					</Button>
					<Button
						variant={
							mobilePane === "code" ? "secondary" : "outline"
						}
						className="h-11 justify-center rounded-[var(--bf-radius-control)] px-3 text-xs font-medium motion-reduce:transition-none"
						aria-pressed={mobilePane === "code"}
						onClick={() => setMobilePane("code")}
						disabled={!hasCodeContent}
						title={
							diffPreview?.path ||
							(openFile
								? openFile.path
								: "Open a file to edit code")
						}
					>
						Code
					</Button>
					<Button
						variant={
							mobilePane === "output" ? "secondary" : "outline"
						}
						className="h-11 justify-center rounded-[var(--bf-radius-control)] px-3 text-xs font-medium motion-reduce:transition-none"
						aria-pressed={mobilePane === "output"}
						onClick={() => setMobilePane("output")}
					>
						Output
					</Button>
				</div>

				{/* Main content area */}
				<div className="relative flex flex-1 min-h-0 overflow-hidden">
					<div
						className={cn(
							"min-h-0 overflow-hidden",
							isDesktop
								? showDesktopSidebar
									? "flex w-auto flex-none"
									: "hidden"
								: showFilesPane
									? "flex w-full flex-1"
									: "hidden",
						)}
						hidden={!isDesktop && !showFilesPane}
					>
						{showDesktopSidebar && <Sidebar />}

						{showDesktopSidebar && (
							<div
								ref={sidebarRef}
								className="relative flex min-w-0 flex-1 flex-col overflow-hidden border-r lg:flex-none"
								style={
									isDesktop
										? { width: `${sidebarWidth}px` }
										: undefined
								}
							>
								<div className="flex-1 overflow-hidden">
									{sidebarPanel === "files" && (
										<WorkspaceFileTree />
									)}
									{sidebarPanel === "search" && (
										<SearchPanel
											onResultOpened={() =>
												setMobilePane("code")
											}
										/>
									)}
									{sidebarPanel === "sourceControl" && (
										<SourceControlPanel />
									)}
									{sidebarPanel === "run" && (
										<RunPanel executeRef={executeRef} />
									)}
									{sidebarPanel === "packages" && (
										<PackagePanel />
									)}
								</div>

								{/* Resize handle */}
								<div
									className="absolute top-0 right-0 bottom-0 hidden lg:block w-1 cursor-col-resize hover:bg-primary/50 active:bg-primary transition-colors"
									onMouseDown={handleMouseDown}
									style={{
										cursor: isResizing
											? "col-resize"
											: "col-resize",
									}}
								/>
							</div>
						)}
					</div>

					<div
						ref={editorRef}
						className={cn(
							"min-w-0 flex-1 flex-col overflow-hidden",
							isDesktop
								? "flex"
								: showCodePane || showOutputPane
									? "flex w-full"
									: "hidden",
						)}
						hidden={!isDesktop && !(showCodePane || showOutputPane)}
					>
						<div
							className={cn(
								"min-h-0 flex-1 flex-col overflow-hidden",
								isDesktop
									? "flex"
									: showCodePane
										? "flex"
										: "hidden",
							)}
							hidden={!isDesktop && !showCodePane}
						>
							<FileTabs
								onEmpty={() => {
									if (isDesktop)
										sidebarButtonRef.current?.focus();
									else filesButtonRef.current?.focus();
								}}
							/>
							<div className="flex-1 overflow-hidden">
								<CodeEditor />
							</div>
						</div>

						<div
							className={cn(
								"overflow-hidden border-t",
								isDesktop
									? "block"
									: showOutputPane
										? "flex min-h-0 flex-1 flex-col"
										: "hidden",
							)}
							hidden={!isDesktop && !showOutputPane}
							style={
								isDesktop
									? { height: `${terminalHeight}px` }
									: undefined
							}
						>
							<TerminalPanel
								onResizeStart={handleTerminalMouseDown}
							/>
						</div>
					</div>
				</div>

				{/* Status bar (includes upload progress) */}
				<StatusBar />
			</div>

			<EditorCloseDialog
				open={showCloseConfirm}
				onOpenChange={setShowCloseConfirm}
				unsavedPaths={unsavedPaths}
				isSaving={isSaving}
				isUploading={isUploading}
				onReturnFocus={() => closeButtonRef.current?.focus()}
				onConfirm={() => {
					if (isSaving) return;
					if (isUploading) cancelUpload();
					closeEditor();
				}}
			/>
		</>
	);
}
