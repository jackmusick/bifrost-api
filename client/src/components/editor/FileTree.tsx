import { useCallback, useState, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import {
	File,
	Folder,
	FilePlus,
	FolderPlus,
	Loader2,
	RefreshCw,
	ShieldCheck,
	AlertTriangle,
	XCircle,
	CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { fileService } from "@/services/fileService";
import { WorkflowIdConflictDialog } from "./WorkflowIdConflictDialog";
import { runPreflight, registerWorkflow } from "@/hooks/useWorkflows";
import { useReloadWorkflowFile } from "@/hooks/useWorkflows";
import { useFileTreeActions } from "@/hooks/useFileTreeActions";
import { FileTreeNode } from "./FileTreeNode";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

type PreflightIssue = {
	level: string;
	category: string;
	detail: string;
	path?: string | null;
};

type PreflightResult = {
	valid: boolean;
	issues: PreflightIssue[];
	warnings: PreflightIssue[];
};

/**
 * File tree component with hierarchical navigation
 */
export function FileTree() {
	const prefersReducedMotion = useReducedMotion();
	const preflightButtonRef = useRef<HTMLButtonElement>(null);
	const {
		// File tree data
		files,
		isLoading,
		isFolderLoading,
		isFolderExpanded,
		openFile,

		// Create actions
		creatingItem,
		creatingInFolder,
		newItemName,
		setNewItemName,
		inputRef,
		handleCreateFile,
		handleCreateFolder,
		handleCancelNewItem: _handleCancelNewItem,
		handleNewItemKeyDown,
		handleInputMouseDown,

		// File/folder actions
		handleFileClick,
		handleFolderToggle,
		handleRefresh,

		// Delete actions
		fileToDelete,
		setFileToDelete,
		handleDelete,
		handleConfirmDelete,

		// Rename actions
		renamingFile,
		renameValue,
		setRenameValue,
		renameInputRef,
		handleRename,
		handleSaveRename: _handleSaveRename,
		handleRenameKeyDown,
		handleRenameInputMouseDown,

		// Drag and drop
		dragOverFolder,
		handleDragStart,
		handleDragOver,
		handleDragLeave,
		handleDrop,

		// Processing state
		isProcessing,

		// Upload conflicts
		uploadConflict,
		uploadWorkflowConflicts,
		setUploadWorkflowConflicts,
	} = useFileTreeActions();

	// Preflight state
	const [preflightLoading, setPreflightLoading] = useState(false);
	const [preflightResult, setPreflightResult] =
		useState<PreflightResult | null>(null);
	const [preflightRegistering, setPreflightRegistering] = useState<
		string | null
	>(null);
	const reloadWorkflows = useReloadWorkflowFile();

	const handlePreflight = useCallback(async () => {
		setPreflightLoading(true);
		try {
			const result = await runPreflight();
			if (
				result.valid &&
				result.warnings.length === 0 &&
				result.issues.length === 0
			) {
				toast.success("All checks passed");
			} else {
				setPreflightResult(result);
			}
		} catch (err) {
			toast.error("Preflight failed", {
				description:
					err instanceof Error ? err.message : String(err),
			});
		} finally {
			setPreflightLoading(false);
		}
	}, []);

	const handlePreflightRegister = useCallback(
		async (path: string, functionName: string) => {
			setPreflightRegistering(functionName);
			try {
				await registerWorkflow(path, functionName);
				toast.success(`Registered ${functionName}`);
				await reloadWorkflows.mutate();
				// Re-run preflight to refresh results
				const result = await runPreflight();
				setPreflightResult(result);
			} catch (err) {
				toast.error("Failed to register", {
					description:
						err instanceof Error ? err.message : String(err),
				});
			} finally {
				setPreflightRegistering(null);
			}
		},
		[reloadWorkflows],
	);

	return (
		<div className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border border-border/70 bg-card shadow-sm">
			{/* Loading overlay */}
			{isProcessing && (
				<div className="absolute inset-0 z-50 flex items-center justify-center rounded-[inherit] bg-background/80 backdrop-blur-sm">
					<div className="flex flex-col items-center gap-2">
						<Loader2 className="h-8 w-8 motion-safe:animate-spin text-primary" />
						<p className="text-sm leading-6 text-muted-foreground">
							Processing...
						</p>
					</div>
				</div>
			)}

			{/* Toolbar */}
			<div className="flex flex-wrap items-center gap-2 border-b border-border/70 bg-muted/30 px-2 py-2">
				<Button
					variant="ghost"
					size="icon-lg"
					onClick={() => handleCreateFile()}
					title="New File"
					aria-label="New File"
					className="shrink-0"
				>
					<FilePlus className="h-4 w-4" />
				</Button>
				<Button
					variant="ghost"
					size="icon-lg"
					onClick={() => handleCreateFolder()}
					title="New Folder"
					aria-label="New Folder"
					className="shrink-0"
				>
					<FolderPlus className="h-4 w-4" />
				</Button>
				<Button
					variant="ghost"
					size="icon-lg"
					onClick={handleRefresh}
					title="Refresh"
					aria-label="Refresh"
					className="shrink-0"
				>
					<RefreshCw
						className={cn(
							"h-4 w-4",
							isLoading && !prefersReducedMotion && "motion-safe:animate-spin",
						)}
					/>
				</Button>
				<Button
					variant="ghost"
					size="icon-lg"
					ref={preflightButtonRef}
					onClick={handlePreflight}
					disabled={preflightLoading}
					title="Preflight Check"
					aria-label="Preflight Check"
					className="shrink-0"
				>
					{preflightLoading ? (
						<Loader2 className="h-4 w-4 motion-safe:animate-spin" />
					) : (
						<ShieldCheck className="h-4 w-4" />
					)}
				</Button>
			</div>

			{/* File list */}
			<div
				className={cn(
					"flex-1 overflow-auto",
					dragOverFolder === "" &&
						"bg-primary/10 outline outline-2 outline-primary outline-dashed",
				)}
				onDragOver={(e) => handleDragOver(e)}
				onDragLeave={handleDragLeave}
				onDrop={(e) => handleDrop(e)}
			>
				{isLoading && files.length === 0 && !creatingItem ? (
					<div className="flex h-full items-center justify-center px-4 py-6">
						<div className="text-sm leading-6 text-muted-foreground">
							Loading files...
						</div>
					</div>
				) : files.length === 0 && !creatingItem ? (
					<div className="flex h-full items-center justify-center px-4 py-6">
						<div className="max-w-sm text-center text-sm leading-6 text-muted-foreground">
							<p>No files found</p>
							<p className="mt-2 text-xs leading-5">
								Use the toolbar to create files and folders
							</p>
						</div>
					</div>
				) : (
					<div className="space-y-1 p-2 sm:p-3">
						{/* Inline new item editor */}
						{creatingItem && !creatingInFolder && (
							<div className="flex items-center gap-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 px-2.5 py-2">
								<div className="w-4" />
								{isProcessing ? (
									<Loader2 className="h-4 w-4 flex-shrink-0 motion-safe:animate-spin text-primary" />
								) : creatingItem === "folder" ? (
									<Folder className="h-4 w-4 flex-shrink-0 text-primary" />
								) : (
									<File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
								)}
								<input
									ref={inputRef}
									type="text"
									value={newItemName}
									onChange={(e) =>
										setNewItemName(e.target.value)
									}
									onKeyDown={handleNewItemKeyDown}
									onMouseDown={handleInputMouseDown}
									placeholder={
										creatingItem === "folder"
											? "Folder name"
											: "File name"
									}
									disabled={isProcessing}
									className="flex-1 bg-transparent text-sm outline-none disabled:opacity-50 disabled:cursor-not-allowed"
								/>
							</div>
						)}

						{/* Existing files */}
						{files.map((file) => (
							<FileTreeNode
								key={file.path}
								file={file}
								onFileClick={handleFileClick}
								onFolderToggle={handleFolderToggle}
								onDelete={handleDelete}
								onRename={handleRename}
								onCreateFile={handleCreateFile}
								onCreateFolder={handleCreateFolder}
								isExpanded={isFolderExpanded(file.path)}
								isLoadingContents={isFolderLoading(file.path)}
								isSelected={openFile?.path === file.path}
								onDragStart={handleDragStart}
								onDragOver={handleDragOver}
								onDragLeave={handleDragLeave}
								onDrop={handleDrop}
								isDragOver={dragOverFolder === file.path}
								creatingItem={creatingItem}
								creatingInFolder={creatingInFolder}
								newItemName={newItemName}
								setNewItemName={setNewItemName}
								inputRef={inputRef}
								handleNewItemKeyDown={handleNewItemKeyDown}
								handleInputMouseDown={handleInputMouseDown}
								handleCancelNewItem={_handleCancelNewItem}
								renamingFile={renamingFile}
								renameValue={renameValue}
								setRenameValue={setRenameValue}
								renameInputRef={renameInputRef}
								handleRenameKeyDown={handleRenameKeyDown}
								handleRenameInputMouseDown={handleRenameInputMouseDown}
								isProcessing={isProcessing}
							/>
						))}
					</div>
				)}
			</div>

			{/* Delete Confirmation Dialog */}
			<AlertDialog
				open={!!fileToDelete}
				onOpenChange={(open) => !open && setFileToDelete(null)}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>
							Delete{" "}
							{fileToDelete?.type === "folder"
								? "Folder"
								: "File"}
						</AlertDialogTitle>
						<AlertDialogDescription>
							Are you sure you want to delete{" "}
							<strong>{fileToDelete?.name}</strong>?
							{fileToDelete?.type === "folder" &&
								" This will delete all contents inside the folder."}{" "}
							This action cannot be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Cancel</AlertDialogCancel>
						<AlertDialogAction
							onClick={handleConfirmDelete}
							className="min-h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							Delete
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>

			{/* Upload Conflict Dialog */}
			<AlertDialog
				open={!!uploadConflict}
				onOpenChange={(open) => {
					if (!open && uploadConflict) {
						uploadConflict.onCancel();
					}
				}}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>
							Replace existing files?
						</AlertDialogTitle>
						<AlertDialogDescription>
							{uploadConflict?.count === 1
								? "1 file already exists and will be replaced."
								: `${uploadConflict?.count} files already exist and will be replaced.`}
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel onClick={uploadConflict?.onCancel}>
							Cancel
						</AlertDialogCancel>
						<AlertDialogAction
							onClick={uploadConflict?.onReplaceAll}
						>
							Replace All
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>

			{/* Workflow ID Conflict Dialog for Uploads */}
			<WorkflowIdConflictDialog
				conflicts={uploadWorkflowConflicts?.conflicts ?? []}
				open={uploadWorkflowConflicts !== null}
				onUseExisting={async () => {
					if (!uploadWorkflowConflicts) return;

					try {
						for (const file of uploadWorkflowConflicts.files) {
							await fileService.writeFile(
								file.filePath,
								file.content,
								file.encoding,
								undefined,
								true,
								file.conflictIds,
							);
						}
						toast.success("Existing workflow IDs preserved");
					} catch (error) {
						console.error("Failed to apply existing IDs:", error);
						toast.error("Failed to preserve workflow IDs");
					}

					setUploadWorkflowConflicts(null);
				}}
				onGenerateNew={() => {
					toast.info("New workflow IDs were generated");
					setUploadWorkflowConflicts(null);
				}}
				onCancel={() => {
					setUploadWorkflowConflicts(null);
				}}
			/>

			{/* Preflight Results Dialog */}
			<Dialog
				open={preflightResult !== null}
				onOpenChange={(open) => {
					if (!open) setPreflightResult(null);
				}}
			>
				<DialogContent onCloseAutoFocus={(event) => { event.preventDefault(); preflightButtonRef.current?.focus(); }} className="w-[min(36rem,calc(100vw-1rem))] max-w-none rounded-[var(--bf-radius-surface)] p-[var(--bf-surface-pad)]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2">
							{preflightResult?.valid ? (
								<CheckCircle2 className="h-5 w-5 text-[var(--bf-success)]" />
							) : (
								<XCircle className="h-5 w-5 text-[var(--bf-danger)]" />
							)}
							Preflight Results
						</DialogTitle>
					</DialogHeader>
					<div className="max-h-80 overflow-y-auto space-y-2">
						{preflightResult?.issues.map((issue, idx) => (
							<div
								key={`issue-${idx}`}
								className="flex items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-3 text-sm leading-6"
							>
								<XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--bf-danger)]" />
								<div className="flex-1 min-w-0">
									{issue.path && (
										<div className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
											{issue.path}
										</div>
									)}
									<div className="[overflow-wrap:anywhere]">{issue.detail}</div>
								</div>
							</div>
						))}
						{preflightResult?.warnings.map((warning, idx) => {
							const fnMatch =
								warning.category === "unregistered_function"
									? warning.detail.match(
											/function '(\w+)'/,
										)
									: null;
							const fnName = fnMatch?.[1];

							return (
								<div
									key={`warn-${idx}`}
									className="flex flex-wrap items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)]/60 p-3 text-sm leading-6"
								>
									<AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--bf-warning)]" />
									<div className="flex-1 min-w-0">
										{warning.path && (
											<div className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
												{warning.path}
											</div>
										)}
										<div className="[overflow-wrap:anywhere]">{warning.detail}</div>
									</div>
									{fnName && warning.path && (
										<Button
											variant="outline"
											size="sm"
											className="min-h-11 text-xs flex-shrink-0"
											disabled={
												preflightRegistering ===
												fnName
											}
											onClick={() =>
												handlePreflightRegister(
													warning.path!,
													fnName,
												)
											}
										>
											{preflightRegistering ===
											fnName ? (
												<Loader2 className="mr-1 h-3 w-3 motion-safe:animate-spin" />
											) : null}
											Register
										</Button>
									)}
								</div>
							);
						})}
						{preflightResult?.issues.length === 0 &&
							preflightResult?.warnings.length === 0 && (
								<div className="py-4 text-center text-sm leading-6 text-muted-foreground">
									All checks passed
								</div>
							)}
				</div>
				</DialogContent>
			</Dialog>
		</div>
	);
}
