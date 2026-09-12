import {
	ChevronRight,
	ChevronDown,
	File,
	Folder,
	Loader2,
	Workflow,
	FileText,
	AppWindow,
	Bot,
	FileCode,
	FileJson,
	FileImage,
	FileSpreadsheet,
	FileArchive,
	FileTerminal,
	Settings,
	FileType,
	Braces,
	type LucideIcon,
} from "lucide-react";
import type { FileTreeNode as FileTreeNodeType } from "@/hooks/useFileTree";
import type { FileMetadata } from "@/services/fileService";
import type { CreatingItemType } from "@/hooks/useFileTreeActions";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { FileTreeContextMenu } from "./FileTreeContextMenu";

/**
 * Platform entity type icons and colors (highest priority)
 */
const ENTITY_TYPE_ICONS: Record<
	string,
	{ icon: LucideIcon; className: string }
> = {
	workflow: { icon: Workflow, className: "text-muted-foreground" },
	form: { icon: FileText, className: "text-muted-foreground" },
	app: { icon: AppWindow, className: "text-muted-foreground" },
	agent: { icon: Bot, className: "text-muted-foreground" },
};

/**
 * File extension icons and colors (fallback when no entity type)
 */
const EXTENSION_ICONS: Record<string, { icon: LucideIcon; className: string }> =
	{
		// Code files
		py: { icon: FileCode, className: "text-muted-foreground" },
		js: { icon: Braces, className: "text-muted-foreground" },
		jsx: { icon: Braces, className: "text-muted-foreground" },
		ts: { icon: Braces, className: "text-muted-foreground" },
		tsx: { icon: Braces, className: "text-muted-foreground" },
		html: { icon: FileCode, className: "text-muted-foreground" },
		css: { icon: FileCode, className: "text-muted-foreground" },
		scss: { icon: FileCode, className: "text-muted-foreground" },
		// Data files
		json: { icon: FileJson, className: "text-muted-foreground" },
		yaml: { icon: FileJson, className: "text-muted-foreground" },
		yml: { icon: FileJson, className: "text-muted-foreground" },
		xml: { icon: FileCode, className: "text-muted-foreground" },
		csv: { icon: FileSpreadsheet, className: "text-muted-foreground" },
		// Text/Docs
		txt: { icon: FileType, className: "text-muted-foreground" },
		md: { icon: FileText, className: "text-muted-foreground" },
		// Shell/Terminal
		sh: { icon: FileTerminal, className: "text-muted-foreground" },
		bash: { icon: FileTerminal, className: "text-muted-foreground" },
		zsh: { icon: FileTerminal, className: "text-muted-foreground" },
		// Images
		png: { icon: FileImage, className: "text-muted-foreground" },
		jpg: { icon: FileImage, className: "text-muted-foreground" },
		jpeg: { icon: FileImage, className: "text-muted-foreground" },
		gif: { icon: FileImage, className: "text-muted-foreground" },
		svg: { icon: FileImage, className: "text-muted-foreground" },
		webp: { icon: FileImage, className: "text-muted-foreground" },
		ico: { icon: FileImage, className: "text-muted-foreground" },
		// Archives
		zip: { icon: FileArchive, className: "text-muted-foreground" },
		tar: { icon: FileArchive, className: "text-muted-foreground" },
		gz: { icon: FileArchive, className: "text-muted-foreground" },
		// Config
		toml: { icon: Settings, className: "text-muted-foreground" },
		ini: { icon: Settings, className: "text-muted-foreground" },
		env: { icon: Settings, className: "text-muted-foreground" },
		gitignore: { icon: Settings, className: "text-muted-foreground" },
	};

/**
 * Get the appropriate icon and styling for a file based on its entity type or extension
 */
export function getFileIcon(
	entityType: string | null | undefined,
	extension: string | null | undefined,
): {
	icon: LucideIcon;
	className: string;
} {
	// Platform entity types take priority
	if (entityType && ENTITY_TYPE_ICONS[entityType]) {
		return ENTITY_TYPE_ICONS[entityType];
	}
	// Fall back to extension-based icons
	if (extension) {
		const ext = extension.toLowerCase();
		if (EXTENSION_ICONS[ext]) {
			return EXTENSION_ICONS[ext];
		}
	}
	// Default file icon
	return { icon: File, className: "text-muted-foreground" };
}

export interface FileTreeNodeProps {
	file: FileTreeNodeType;
	onFileClick: (file: FileMetadata) => void;
	onFolderToggle: (folder: FileMetadata) => void;
	onDelete: (file: FileMetadata) => void;
	onRename: (file: FileMetadata) => void;
	onCreateFile: (folderPath?: string) => void;
	onCreateFolder: (folderPath?: string) => void;
	isExpanded: boolean;
	isLoadingContents: boolean;
	isSelected: boolean;
	onDragStart: (e: React.DragEvent, file: FileMetadata) => void;
	onDragOver: (e: React.DragEvent, targetFolder?: string) => void;
	onDragLeave: () => void;
	onDrop: (e: React.DragEvent, targetFolder?: string) => void;
	isDragOver: boolean;
	creatingItem: CreatingItemType;
	creatingInFolder: string | null;
	newItemName: string;
	setNewItemName: (name: string) => void;
	inputRef: React.RefObject<HTMLInputElement | null>;
	handleNewItemKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
	handleInputMouseDown: (e: React.MouseEvent) => void;
	handleCancelNewItem: () => void;
	renamingFile: FileMetadata | null;
	renameValue: string;
	setRenameValue: (name: string) => void;
	renameInputRef: React.RefObject<HTMLInputElement | null>;
	handleRenameKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
	handleRenameInputMouseDown: (e: React.MouseEvent) => void;
	isProcessing: boolean;
}

export function FileTreeNode({
	file,
	onFileClick,
	onFolderToggle,
	onDelete,
	onRename,
	onCreateFile,
	onCreateFolder,
	isExpanded,
	isLoadingContents,
	isSelected,
	onDragStart,
	onDragOver,
	onDragLeave,
	onDrop,
	isDragOver,
	creatingItem,
	creatingInFolder,
	newItemName,
	setNewItemName,
	inputRef,
	handleNewItemKeyDown,
	handleInputMouseDown,
	handleCancelNewItem: _handleCancelNewItem,
	renamingFile,
	renameValue,
	setRenameValue,
	renameInputRef,
	handleRenameKeyDown,
	handleRenameInputMouseDown,
	isProcessing,
}: FileTreeNodeProps) {
	const isFolder = file.type === "folder";
	const level = file.level;
	const isRenaming = renamingFile?.path === file.path;

	return (
		<div>
			{isRenaming ? (
				// Inline rename editor
				<div
					className="flex items-center gap-2 rounded-[var(--bf-radius-control)] px-2 py-1 bg-muted/50"
					style={{ paddingLeft: `min(${level * 12 + 8}px, 25%)` }}
				>
					{isFolder ? (
						<>
							{isLoadingContents ? (
								<Loader2 className="h-4 w-4 flex-shrink-0 motion-safe:animate-spin text-muted-foreground" />
							) : isExpanded ? (
								<ChevronDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
							) : (
								<ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
							)}
							<Folder className="h-4 w-4 flex-shrink-0 text-primary" />
						</>
					) : (
						(() => {
							const { icon: FileIcon, className } = getFileIcon(
								file.entity_type,
								file.extension,
							);
							return (
								<>
									<div className="w-4 shrink-0" />
									<FileIcon
										className={cn(
											"h-4 w-4 flex-shrink-0",
											className,
										)}
									/>
								</>
							);
						})()
					)}
					<Input
						aria-label={`Rename ${file.name}`}
						ref={renameInputRef}
						type="text"
						value={renameValue}
						onChange={(e) => setRenameValue(e.target.value)}
						onKeyDown={handleRenameKeyDown}
						onMouseDown={handleRenameInputMouseDown}
						disabled={isProcessing}
						className="min-w-0 min-h-11 flex-1 text-base sm:text-sm"
					/>
				</div>
			) : (
				<FileTreeContextMenu
					file={file}
					isFolder={isFolder}
					onCreateFile={onCreateFile}
					onCreateFolder={onCreateFolder}
					onRename={onRename}
					onDelete={onDelete}
				>
					<button
						type="button"
						aria-expanded={isFolder ? isExpanded : undefined}
						aria-pressed={!isFolder ? isSelected : undefined}
						draggable
						onClick={() => {
							if (isFolder) {
								onFolderToggle(file);
							} else {
								onFileClick(file);
							}
						}}
						onDragStart={(e) => onDragStart(e, file)}
						onDragOver={(e) => {
							if (isFolder) {
								e.stopPropagation();
								onDragOver(e, file.path);
							}
						}}
						onDragLeave={onDragLeave}
						onDrop={(e) => {
							if (isFolder) {
								e.stopPropagation();
								onDrop(e, file.path);
							}
						}}
						className={cn(
							"flex min-h-11 min-w-0 w-full items-center gap-2 rounded-[var(--bf-radius-control)] px-2 py-1 text-left text-sm transition-colors motion-reduce:transition-none outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
							isSelected && !isDragOver
								? "bg-accent text-accent-foreground"
								: "",
							!isDragOver && !isSelected ? "hover:bg-muted" : "",
							isDragOver &&
								isFolder &&
								"bg-primary/10 ring-2 ring-inset ring-primary",
						)}
						style={{ paddingLeft: `min(${level * 12 + 8}px, 25%)` }}
					>
						{isFolder && (
							<>
								{isLoadingContents ? (
									<Loader2 className="h-4 w-4 flex-shrink-0 motion-safe:animate-spin text-muted-foreground" />
								) : isExpanded ? (
									<ChevronDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
								) : (
									<ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
								)}
								<Folder className="h-4 w-4 flex-shrink-0 text-primary" />
							</>
						)}
						{!isFolder &&
							(() => {
								const { icon: FileIcon, className } =
									getFileIcon(
										file.entity_type,
										file.extension,
									);
								return (
									<>
										<div className="w-4 shrink-0" />
										<FileIcon
											className={cn(
												"h-4 w-4 flex-shrink-0",
												className,
											)}
										/>
									</>
								);
							})()}
						<span className="min-w-0 flex-1 [overflow-wrap:anywhere]">
							{file.name}
						</span>
					</button>
				</FileTreeContextMenu>
			)}

			{/* Inline new item editor (shown when creating in this folder) */}
			{creatingItem && creatingInFolder === file.path && (
				<div
					className="flex items-center gap-2 rounded-[var(--bf-radius-control)] px-2 py-1 bg-muted/50 mt-1"
					style={{
						paddingLeft: `min(${(level + 1) * 12 + 8}px, 25%)`,
					}}
				>
					<div className="w-4 shrink-0" />
					{isProcessing ? (
						<Loader2 className="h-4 w-4 flex-shrink-0 motion-safe:animate-spin text-primary" />
					) : creatingItem === "folder" ? (
						<Folder className="h-4 w-4 flex-shrink-0 text-primary" />
					) : (
						<File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
					)}
					<Input
						aria-label={
							creatingItem === "folder"
								? "Folder name"
								: "File name"
						}
						ref={inputRef}
						type="text"
						value={newItemName}
						onChange={(e) => setNewItemName(e.target.value)}
						onKeyDown={handleNewItemKeyDown}
						onMouseDown={handleInputMouseDown}
						placeholder={
							creatingItem === "folder"
								? "Folder name"
								: "File name"
						}
						disabled={isProcessing}
						className="min-w-0 min-h-11 flex-1 text-base sm:text-sm"
					/>
				</div>
			)}
		</div>
	);
}
