import { useRef, useState } from "react";
import { FileText, Folder, RotateCcw, Upload } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { FileEntryActions } from "./FileEntryActions";
import { Button } from "@/components/ui/button";
import {
	ContextMenu,
	ContextMenuSeparator,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { files } from "@/lib/app-sdk/files";
import { listStructure, type StructureEntry } from "@/services/fileStructure";
import { EntryMenuItem, FileContextMenuContent } from "./fileContextMenu";
import { InlineLoader } from "./InlineLoader";
import { useFileUpload } from "./useFileUpload";

export type ListingRowAction =
	"preview" | "download" | "delete" | "policy" | "test";

export type ListingFolderAction = "effective" | "test" | "newPolicy" | "upload";

interface FolderListingProps {
	scope: string | null;
	location: string | null;
	prefix: string;
	readOnly: boolean;
	managedBySolution?: boolean;
	solutionId?: string | null;
	onOpenFolder: (prefix: string) => void;
	onSelectFile: (path: string) => void;
	onRowAction: (action: ListingRowAction, path: string) => void;
	onFolderAction: (action: ListingFolderAction, prefix: string) => void;
	onUploaded: () => void;
}

export function FolderListing({
	scope,
	location,
	prefix,
	readOnly,
	managedBySolution = false,
	solutionId = null,
	onOpenFolder,
	onSelectFile,
	onRowAction,
	onFolderAction,
	onUploaded,
}: FolderListingProps) {
	const compactLayout = useMediaQuery("(max-width: 1023px)");
	const listing = useQuery({
		queryKey: ["file-structure", scope, location, prefix],
		queryFn: () => listStructure(location!, prefix, scope),
		enabled: location !== null,
		retry: false,
	});
	const entries = listing.data ?? [];
	const loading = listing.isPending;
	const [downloadError, setDownloadError] = useState<{
		path: string;
		message: string;
	} | null>(null);
	const [downloading, setDownloading] = useState<string | null>(null);
	const [dragOver, setDragOver] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const { uploading, uploadFiles, progress, error, retryUpload } =
		useFileUpload(readOnly ? null : location, scope, prefix, onUploaded);

	async function handleDownload(path: string) {
		if (location === null || downloading) return;
		setDownloading(path);
		setDownloadError(null);
		let url: string | undefined;
		try {
			const blob = await files.download(path, { location, scope });
			if (typeof URL.createObjectURL !== "function")
				throw new Error("Downloads are unavailable in this browser.");
			url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = path.split("/").at(-1) ?? "download";
			link.click();
		} catch (error) {
			setDownloadError({
				path,
				message:
					error instanceof Error
						? error.message.replace(
								/^files\.download:\s*\d+\s*/,
								"",
							)
						: "Try downloading this file again.",
			});
		} finally {
			if (url) URL.revokeObjectURL(url);
			setDownloading(null);
		}
	}

	const folders = entries.filter((e) => e.kind === "folder");
	const fileEntries = entries.filter((e) => e.kind === "file");
	const canUpload = !readOnly && location !== null;
	const managedBadge = managedBySolution ? (
		<SolutionManagedBadge solutionId={solutionId ?? undefined} />
	) : null;

	const renderActions = (entry: StructureEntry) => (
		<FileEntryActions
			entry={entry}
			readOnly={readOnly}
			downloading={downloading !== null}
			onAction={(action, path) => {
				if (action === "download") void handleDownload(path);
				else if (entry.kind === "folder")
					onFolderAction(action as ListingFolderAction, path);
				else onRowAction(action as ListingRowAction, path);
			}}
		/>
	);

	const renderMobileEntry = (entry: StructureEntry) => {
		const isFolder = entry.kind === "folder";
		const Icon = isFolder ? Folder : FileText;

		return (
			<li
				key={entry.path}
				className="min-w-0 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4"
			>
				<div className="flex items-start gap-3">
					<Icon className="mt-3 size-5 shrink-0 text-muted-foreground" />
					<div className="min-w-0 flex-1">
						<button
							type="button"
							className="min-h-11 text-left text-sm font-medium [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring"
							onClick={() =>
								isFolder
									? onOpenFolder(entry.path)
									: onSelectFile(entry.path)
							}
						>
							{entry.name}
						</button>
						<p className="text-xs text-muted-foreground">
							{isFolder ? "Folder" : "File"}
						</p>
						{managedBadge}
					</div>
					{renderActions(entry)}
				</div>
			</li>
		);
	};

	return (
		<section
			className="relative flex min-h-0 flex-1 flex-col"
			onDragOver={(event) => {
				if (readOnly || location === null) return;
				event.preventDefault();
				setDragOver(true);
			}}
			onDragLeave={(event) => {
				// Only clear when the cursor actually leaves the section, not
				// when it crosses a child element boundary.
				if (event.currentTarget.contains(event.relatedTarget as Node))
					return;
				setDragOver(false);
			}}
			onDrop={(event) => {
				event.preventDefault();
				setDragOver(false);
				if (event.dataTransfer.files.length)
					void uploadFiles(event.dataTransfer.files);
			}}
		>
			{canUpload && (
				<input
					ref={fileInputRef}
					type="file"
					multiple
					className="hidden"
					onChange={(event) => {
						if (event.target.files?.length)
							void uploadFiles(event.target.files);
						event.target.value = "";
					}}
				/>
			)}
			{/* Full-pane drag overlay — visible while dragging files over the
			    listing, so the whole area reads as a dropzone. */}
			{dragOver && canUpload && (
				<div className="pointer-events-none absolute inset-0 z-10 m-1 flex items-center justify-center rounded-[var(--bf-radius-feature)] border-2 border-dashed border-primary/60 bg-primary/5 backdrop-blur-[1px]">
					<div className="flex flex-col items-center gap-2 text-sm font-medium text-primary">
						<Upload className="h-6 w-6" />
						Drop to upload to {prefix || "/"}
					</div>
				</div>
			)}
			<div className="min-h-0 flex-1 overflow-auto p-2">
				{downloadError && (
					<Alert variant="destructive" className="mb-3">
						<AlertTitle>Download failed</AlertTitle>
						<AlertDescription>
							<p className="[overflow-wrap:anywhere]">
								{downloadError.path}: {downloadError.message}
							</p>
							<Button
								variant="outline"
								className="mt-3 min-h-11"
								onClick={() =>
									void handleDownload(downloadError.path)
								}
							>
								Retry download
							</Button>
						</AlertDescription>
					</Alert>
				)}
				{downloading && (
					<p
						role="status"
						className="mb-3 text-sm text-muted-foreground [overflow-wrap:anywhere]"
					>
						Downloading {downloading}…
					</p>
				)}
				{progress && (
					<p
						role="status"
						aria-live="polite"
						className="mb-3 text-sm text-muted-foreground [overflow-wrap:anywhere]"
					>
						{progress}
					</p>
				)}
				{error && (
					<Alert variant="destructive" className="mb-3">
						<AlertTitle>Upload failed</AlertTitle>
						<AlertDescription>
							<p className="[overflow-wrap:anywhere]">{error}</p>
							<Button
								variant="outline"
								className="mt-3 min-h-11"
								onClick={() => retryUpload()}
							>
								<RotateCcw className="h-4 w-4" />
								Retry upload
							</Button>
						</AlertDescription>
					</Alert>
				)}
				{location !== null && listing.isError && (
					<Alert variant="destructive" className="mb-3">
						<AlertTitle>Folder could not be loaded</AlertTitle>
						<AlertDescription>
							<p>
								{listing.data
									? "Showing the last loaded items."
									: "Try loading this folder again."}
							</p>
							<Button
								variant="outline"
								className="mt-3 min-h-11"
								onClick={() => void listing.refetch()}
							>
								Retry folder
							</Button>
						</AlertDescription>
					</Alert>
				)}
				{location === null ? (
					<p className="p-4 text-sm text-muted-foreground">
						Choose a share to browse its folders and files.
					</p>
				) : loading ? (
					<InlineLoader label="Loading folder…" className="p-4" />
				) : listing.isError && !listing.data ? null : entries.length ===
				  0 ? (
					canUpload ? (
						<button
							type="button"
							onClick={() => fileInputRef.current?.click()}
							disabled={uploading}
							className="flex h-full min-h-[12rem] w-full flex-col items-center justify-center gap-2 rounded-[var(--bf-radius-feature)] border-2 border-dashed border-border p-6 text-sm text-muted-foreground transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none hover:border-primary/50 hover:text-foreground"
						>
							<Upload className="h-7 w-7" />
							<span className="font-medium">
								{uploading
									? "Uploading…"
									: compactLayout
										? "Tap to upload files"
										: "Drag files here or click to upload"}
							</span>
							<span className="text-xs">
								Uploads to {prefix || "/"}
							</span>
						</button>
					) : (
						<p className="p-4 text-sm text-muted-foreground">
							No files here.
						</p>
					)
				) : compactLayout ? (
					<ul aria-label="Folders and files" className="space-y-3">
						{[...folders, ...fileEntries].map(renderMobileEntry)}
					</ul>
				) : (
					<DataTable>
						<DataTableHeader>
							<DataTableRow>
								<DataTableHead>Name</DataTableHead>
								<DataTableHead className="w-32 text-right">
									Actions
								</DataTableHead>
							</DataTableRow>
						</DataTableHeader>
						<DataTableBody>
							{folders.map((folder) => (
								<ContextMenu key={folder.path}>
									<ContextMenuTrigger asChild>
										<DataTableRow
											clickable
											onClick={() =>
												onOpenFolder(folder.path)
											}
										>
											<DataTableCell>
												<div className="flex min-w-0 items-center gap-2">
													<Folder className="h-4 w-4 text-muted-foreground" />
													<button
														type="button"
														className="min-h-8 text-left [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring"
														onClick={(event) => {
															event.stopPropagation();
															onOpenFolder(
																folder.path,
															);
														}}
													>
														{folder.name}
													</button>
													{managedBadge}
												</div>
											</DataTableCell>
											<DataTableCell className="text-right">
												{renderActions(folder)}
											</DataTableCell>
										</DataTableRow>
									</ContextMenuTrigger>
									<FileContextMenuContent>
										<EntryMenuItem
											action="effective"
											onSelect={() =>
												onFolderAction(
													"effective",
													folder.path,
												)
											}
										/>
										<EntryMenuItem
											action="test"
											onSelect={() =>
												onFolderAction(
													"test",
													folder.path,
												)
											}
										/>
										{!readOnly && (
											<>
												<EntryMenuItem
													action="upload"
													onSelect={() =>
														onFolderAction(
															"upload",
															folder.path,
														)
													}
												/>
												<EntryMenuItem
													action="newPolicy"
													onSelect={() =>
														onFolderAction(
															"newPolicy",
															folder.path,
														)
													}
												/>
											</>
										)}
									</FileContextMenuContent>
								</ContextMenu>
							))}
							{fileEntries.map((file) => (
								<ContextMenu key={file.path}>
									<ContextMenuTrigger asChild>
										<DataTableRow
											clickable
											onClick={() =>
												onSelectFile(file.path)
											}
										>
											<DataTableCell>
												<div className="flex min-w-0 items-center gap-2">
													<FileText className="h-4 w-4 text-muted-foreground" />
													<button
														type="button"
														className="min-h-8 text-left [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring"
														onClick={(event) => {
															event.stopPropagation();
															onSelectFile(
																file.path,
															);
														}}
													>
														{file.name}
													</button>
													{managedBadge}
												</div>
											</DataTableCell>
											<DataTableCell>
												<div className="flex justify-end">
													{renderActions(file)}
												</div>
											</DataTableCell>
										</DataTableRow>
									</ContextMenuTrigger>
									<FileContextMenuContent>
										<EntryMenuItem
											action="preview"
											onSelect={() =>
												onRowAction(
													"preview",
													file.path,
												)
											}
										/>
										<EntryMenuItem
											action="test"
											onSelect={() =>
												onRowAction("test", file.path)
											}
										/>
										{!readOnly && (
											<EntryMenuItem
												action="policy"
												onSelect={() =>
													onRowAction(
														"policy",
														file.path,
													)
												}
											/>
										)}
										<EntryMenuItem
											action="download"
											onSelect={() =>
												void handleDownload(file.path)
											}
										/>
										{!readOnly && (
											<>
												<ContextMenuSeparator />
												<EntryMenuItem
													action="delete"
													destructive
													onSelect={() =>
														onRowAction(
															"delete",
															file.path,
														)
													}
												/>
											</>
										)}
									</FileContextMenuContent>
								</ContextMenu>
							))}
						</DataTableBody>
					</DataTable>
				)}
			</div>
		</section>
	);
}
