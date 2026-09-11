import { useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { FilesInspector } from "./FilesInspector";
import {
	ChevronLeft,
	Menu,
	Plus,
	Upload,
	Info,
	FolderOpen,
	ShieldCheck,
	HardDrive,
} from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { type FilePolicy } from "@/services/filePolicies";
import { useAuth } from "@/contexts/AuthContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useOrganizations } from "@/hooks/useOrganizations";
import { Breadcrumbs } from "./Breadcrumbs";
import { EffectiveAccessPanel } from "./EffectiveAccessPanel";
import { FilePreview } from "./FilePreview";
import { FolderListing, type ListingRowAction } from "./FolderListing";
import {
	DeleteConfirmation,
	type FileDeleteTarget,
} from "./DeleteConfirmation";
import { NewShareDialog } from "./NewShareDialog";
import { PoliciesView } from "./PoliciesView";
import { PolicyEditorModal } from "./PolicyEditorModal";
import { SharesOverview } from "./SharesOverview";
import { ShareTree, type ShareTreeAction } from "./ShareTree";
import { TestAccessModal } from "./TestAccessModal";
import { useFileUpload } from "./useFileUpload";

const READ_ONLY_LOCATIONS = new Set(["uploads"]);

interface FilesExplorerProps {
	/**
	 * When set, the explorer is pinned to the solution install's file scope:
	 * scope=<install_id>. The org/global selector is hidden and the header shows
	 * a back-link to the Solution detail page.
	 */
	install?: string;
	/** Display name for the pinned Solution install. */
	installName?: string;
	/** Render inside another page surface, without the solution back-link chrome. */
	embedded?: boolean;
}

export function FilesExplorer({
	install,
	installName,
	embedded = false,
}: FilesExplorerProps = {}) {
	const { isPlatformAdmin } = useAuth();
	const explorerRef = useRef<HTMLDivElement>(null);
	const detailTriggerRef = useRef<HTMLElement | null>(null);
	const [deleteTarget, setDeleteTarget] = useState<FileDeleteTarget | null>(
		null,
	);
	const queryClient = useQueryClient();
	function refreshFiles() {
		void queryClient.invalidateQueries({ queryKey: ["file-structure"] });
		void queryClient.invalidateQueries({ queryKey: ["file-shares"] });
		setRefreshKey((key) => key + 1);
	}
	const { data: organizations = [] } = useOrganizations({
		enabled: isPlatformAdmin && !install,
	});
	const isWide = useMediaQuery("(min-width: 1024px)");
	const isThreePane = useMediaQuery("(min-width: 1280px)");

	// When `install` is set, scope and location are pinned — not user-controlled.
	// Otherwise selectorScope is what OrganizationSelect speaks: null = Global.
	// The data layer needs the EXPLICIT "global" string (not null/UNSET) so
	// write/upload (`resolve_target_org`) and the structural list agree — null
	// would resolve to the caller's own org on the write path while the explorer
	// means literal global.
	const [selectorScope, setSelectorScope] = useState<string | null>(null);
	const scope = install ?? selectorScope ?? "global";
	const [location, setLocation] = useState<string | null>(null);
	const [prefix, setPrefix] = useState("");
	const [selectedFile, setSelectedFile] = useState<string | null>(null);
	const [view, setView] = useState<"browse" | "policies">("browse");

	const [treeOpen, setTreeOpen] = useState(false);
	const [detailOpen, setDetailOpen] = useState(false);
	const [newShareOpen, setNewShareOpen] = useState(false);
	const [testOpen, setTestOpen] = useState(false);
	const [policyOpen, setPolicyOpen] = useState(false);
	// The (location, path) a modal targets — may be a folder prefix or a file.
	const [modalTarget, setModalTarget] = useState<{
		location: string;
		path: string;
	}>({ location: "", path: "" });
	// Bump to force ShareTree/FolderListing to refetch after a mutation.
	const [refreshKey, setRefreshKey] = useState(0);

	const solutionReadOnly = Boolean(install);
	const readOnly =
		solutionReadOnly ||
		(location !== null && READ_ONLY_LOCATIONS.has(location));
	const canUpload = view === "browse" && location !== null && !readOnly;
	const uploadInputRef = useRef<HTMLInputElement>(null);
	const {
		uploading,
		uploadFiles,
		progress: uploadProgress,
		error: uploadError,
		retryUpload,
	} = useFileUpload(canUpload ? location : null, scope, prefix, refreshFiles);
	const scopeLabel = useMemo(() => {
		if (install) return "Solution";
		if (selectorScope === null) return "Global";
		return (
			organizations.find((o) => o.id === selectorScope)?.name ??
			"Organization"
		);
	}, [install, selectorScope, organizations]);
	const segments = prefix ? prefix.replace(/\/$/, "").split("/") : [];

	function openDetails() {
		detailTriggerRef.current =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;
		setDetailOpen(true);
	}

	function closeDetails() {
		// Remove inert before restoring focus to the directory on small screens.
		flushSync(() => setDetailOpen(false));
		const opener = detailTriggerRef.current;
		if (opener?.isConnected && opener !== document.body)
			opener.focus({ preventScroll: true });
		else explorerRef.current?.focus({ preventScroll: true });
	}

	function resetTo(nextLocation: string | null, nextPrefix: string) {
		setLocation(nextLocation);
		setPrefix(nextPrefix);
		setSelectedFile(null);
		setDetailOpen(false);
	}

	function handleScopeChange(next: string | null | undefined) {
		setSelectorScope(next ?? null);
		resetTo(null, "");
	}

	function handleSelect(nextLocation: string, nextPrefix: string) {
		resetTo(nextLocation, nextPrefix);
		setTreeOpen(false);
		setView("browse");
	}

	function handleBreadcrumb(depth: number) {
		if (install && depth === 0) {
			resetTo(location, "");
			return;
		}
		if (install) {
			resetTo(location, segments.slice(0, depth).join("/"));
			return;
		}
		if (depth === -1) {
			resetTo(null, "");
		} else if (depth === 0) {
			resetTo(location, "");
		} else {
			resetTo(location, segments.slice(0, depth).join("/"));
		}
	}

	function openTest(loc: string, path: string) {
		setModalTarget({ location: loc, path });
		setTestOpen(true);
	}

	function openPolicy(loc: string, path: string) {
		if (solutionReadOnly) return;
		setModalTarget({ location: loc, path });
		setPolicyOpen(true);
	}

	function handleDeletePolicy(policy: FilePolicy) {
		if (solutionReadOnly) return;
		setDeleteTarget({ kind: "policy", policy });
	}

	function handleTreeAction(
		action: ShareTreeAction,
		loc: string,
		treePrefix: string,
	) {
		if (action === "effective") {
			handleSelect(loc, treePrefix);
			openDetails();
		} else if (action === "test") {
			openTest(loc, treePrefix);
		} else if (action === "newPolicy") {
			if (solutionReadOnly) return;
			openPolicy(loc, treePrefix);
		} else if (action === "upload") {
			if (solutionReadOnly || READ_ONLY_LOCATIONS.has(loc)) return;
			// Commit the destination before invoking the browser file chooser.
			flushSync(() => handleSelect(loc, treePrefix));
			uploadInputRef.current?.click();
		}
	}

	function handleRowAction(action: ListingRowAction, path: string) {
		if (location === null) return;
		if (readOnly && (action === "policy" || action === "delete")) return;
		if (action === "preview") {
			setSelectedFile(path);
			openDetails();
		} else if (action === "test") {
			openTest(location, path);
		} else if (action === "policy") {
			openPolicy(location, path);
		} else if (action === "delete") {
			setDeleteTarget({ kind: "file", location, scope, path });
		}
	}

	function selectFile(path: string) {
		setSelectedFile(path);
		openDetails();
	}

	const tree = (
		<ShareTree
			key={`tree-${scope}-${refreshKey}`}
			scope={scope}
			selectedLocation={location}
			selectedPrefix={prefix}
			readOnly={solutionReadOnly}
			onSelect={handleSelect}
			onContextAction={handleTreeAction}
		/>
	);

	const preview = (
		<FilePreview
			location={location ?? ""}
			scope={scope}
			path={selectedFile}
		/>
	);
	const access = (
		<EffectiveAccessPanel
			key={refreshKey}
			location={location ?? ""}
			scope={scope}
			path={selectedFile ?? (location ? prefix : null)}
			readOnly={readOnly}
			managedBySolution={solutionReadOnly}
			solutionId={install}
			onOpenTest={() => openTest(location ?? "", selectedFile ?? prefix)}
			onManagePolicy={() =>
				openPolicy(location ?? "", selectedFile ?? prefix)
			}
		/>
	);
	const detail = (
		<Tabs
			key={selectedFile ?? "access"}
			defaultValue={selectedFile ? "preview" : "access"}
			className="flex min-h-0 flex-1 flex-col gap-0"
			data-testid="detail-pane"
		>
			<TabsList
				variant="line"
				aria-label="File details"
				className="mx-4 mt-2 shrink-0"
			>
				{selectedFile && (
					<TabsTrigger value="preview" className="min-h-11">
						Preview
					</TabsTrigger>
				)}
				<TabsTrigger value="access" className="min-h-11">
					Access
				</TabsTrigger>
			</TabsList>
			<TabsContent
				value="preview"
				className="min-h-0 flex-1 overflow-hidden"
			>
				{preview}
			</TabsContent>
			<TabsContent
				value="access"
				className="min-h-0 flex-1 overflow-hidden"
			>
				{access}
			</TabsContent>
		</Tabs>
	);
	const solutionTitle = installName ?? "Solution";
	const showTree = isWide && (!detailOpen || isThreePane);

	return (
		<div
			ref={explorerRef}
			tabIndex={-1}
			role="region"
			aria-label="Files explorer"
			className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border bg-card outline-none"
		>
			<header className="flex shrink-0 flex-wrap items-center gap-3 border-b bg-muted/20 px-3 py-2 sm:px-4">
				{install && !embedded && (
					<div className="flex min-w-0 flex-1 items-center gap-2">
						<Button
							asChild
							variant="ghost"
							size="icon"
							aria-label="Back to Solution"
						>
							<Link
								to={`/solutions/${install}`}
								data-testid="files-solution-back"
							>
								<ChevronLeft className="size-4" />
							</Link>
						</Button>
						<span
							className="min-w-0 text-sm font-semibold [overflow-wrap:anywhere]"
							title={solutionTitle}
						>
							{solutionTitle}
						</span>
					</div>
				)}
				{isPlatformAdmin && !install && (
					<div className="min-w-0 w-full sm:w-56 sm:shrink-0">
						<OrganizationSelect
							aria-label="File scope"
							value={selectorScope}
							onChange={handleScopeChange}
							showGlobal
							showAll={false}
						/>
					</div>
				)}
				{!install && (
					<Tabs
						value={view}
						onValueChange={(value) => {
							setView(value as "browse" | "policies");
							setDetailOpen(false);
						}}
						className="min-w-0"
					>
						<TabsList variant="line" aria-label="Files workspace">
							<TabsTrigger value="browse" className="min-h-11">
								<FolderOpen className="size-4" />
								Files
							</TabsTrigger>
							<TabsTrigger value="policies" className="min-h-11">
								<ShieldCheck className="size-4" />
								Access Policies
							</TabsTrigger>
						</TabsList>
					</Tabs>
				)}
				{!install && (
					<Button
						type="button"
						variant="outline"
						size="sm"
						aria-label="New Share"
						className="ml-auto min-h-11 w-11 shrink-0 px-0 sm:min-h-9 sm:w-auto sm:px-3"
						onClick={() => setNewShareOpen(true)}
					>
						<Plus className="size-4" />
						<span className="hidden sm:inline">New Share</span>
					</Button>
				)}
			</header>
			<div className="relative flex min-h-0 flex-1 overflow-hidden">
				{showTree && (
					<aside
						aria-label="Share navigation"
						className="flex w-56 shrink-0 flex-col border-r bg-muted/10"
					>
						<div className="flex min-h-14 items-center gap-2 border-b px-4 text-sm font-semibold">
							<HardDrive className="size-4 text-primary" />
							Shares
						</div>
						{tree}
					</aside>
				)}
				<div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
					<div
						inert={!isWide && detailOpen ? true : undefined}
						className="flex min-h-0 flex-1 flex-col"
					>
						{view === "browse" && (
							<div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-3 py-2 sm:px-4">
								{!showTree && (
									<Sheet
										open={treeOpen}
										onOpenChange={setTreeOpen}
									>
										<SheetTrigger asChild>
											<Button
												variant="outline"
												size="icon"
												aria-label="Open shares"
											>
												<Menu className="size-4" />
											</Button>
										</SheetTrigger>
										<SheetContent
											side="left"
											className="w-72 p-0"
										>
											<SheetHeader>
												<SheetTitle>Shares</SheetTitle>
											</SheetHeader>
											<div className="flex min-h-0 flex-1 flex-col">
												{tree}
											</div>
										</SheetContent>
									</Sheet>
								)}
								<div className="min-w-0 flex-1">
									<Breadcrumbs
										scopeLabel={
											install ? solutionTitle : scopeLabel
										}
										includeScopeRoot={!install}
										location={location}
										segments={segments}
										onNavigate={handleBreadcrumb}
									/>
								</div>
								{view === "browse" && location !== null && (
									<Button
										variant="ghost"
										size="sm"
										className="min-h-11 sm:min-h-9"
										onClick={() => {
											setSelectedFile(null);
											openDetails();
										}}
									>
										<Info className="size-4" />
										Folder Details
									</Button>
								)}
								{canUpload && (
									<>
										<input
											ref={uploadInputRef}
											type="file"
											multiple
											className="hidden"
											onChange={(event) => {
												if (event.target.files?.length)
													void uploadFiles(
														event.target.files,
													);
												event.target.value = "";
											}}
										/>
										<Button
											size="sm"
											className="min-h-11 sm:min-h-9"
											onClick={() =>
												uploadInputRef.current?.click()
											}
											disabled={uploading}
										>
											<Upload className="size-4" />
											{uploading
												? "Uploading…"
												: "Upload"}
										</Button>
									</>
								)}
							</div>
						)}
						{uploadProgress && (
							<p
								role="status"
								className="border-b px-4 py-2 text-sm text-muted-foreground [overflow-wrap:anywhere]"
							>
								{uploadProgress}
							</p>
						)}
						{uploadError && (
							<Alert variant="destructive" className="m-3 w-auto">
								<AlertTitle>Upload failed</AlertTitle>
								<AlertDescription>
									<p>{uploadError}</p>
									<Button
										variant="outline"
										className="mt-2"
										disabled={uploading}
										onClick={() => void retryUpload()}
									>
										Retry upload
									</Button>
								</AlertDescription>
							</Alert>
						)}
						{view === "policies" && !install ? (
							<PoliciesView
								scope={scope}
								refreshKey={refreshKey}
								onEdit={(policy) =>
									openPolicy(policy.location, policy.path)
								}
								onDelete={handleDeletePolicy}
							/>
						) : location === null ? (
							<SharesOverview
								scope={scope}
								readOnly={solutionReadOnly}
								onSelect={handleSelect}
							/>
						) : (
							<FolderListing
								key={`listing-${scope}-${location}-${prefix}`}
								scope={scope}
								location={location}
								prefix={prefix}
								readOnly={readOnly}
								managedBySolution={solutionReadOnly}
								solutionId={install}
								selectedPath={detailOpen ? selectedFile : null}
								onOpenFolder={(next) => resetTo(location, next)}
								onSelectFile={selectFile}
								onRowAction={handleRowAction}
								onFolderAction={(action, folderPrefix) =>
									handleTreeAction(
										action,
										location,
										folderPrefix,
									)
								}
								onUploaded={refreshFiles}
							/>
						)}
					</div>
					{!isWide && (
						<AnimatePresence initial={false}>
							{detailOpen && (
								<FilesInspector
									key="file-inspector"
									inline={false}
									title={
										selectedFile?.split("/").pop() ??
										segments.at(-1) ??
										location ??
										"Details"
									}
									path={`${location ?? ""}/${selectedFile ?? prefix}`}
									isFile={Boolean(selectedFile)}
									onClose={closeDetails}
								>
									{detail}
								</FilesInspector>
							)}
						</AnimatePresence>
					)}
				</div>
				{isWide && (
					<AnimatePresence initial={false}>
						{detailOpen && (
							<FilesInspector
								key="file-inspector"
								inline
								title={
									selectedFile?.split("/").pop() ??
									segments.at(-1) ??
									location ??
									"Details"
								}
								path={`${location ?? ""}/${selectedFile ?? prefix}`}
								isFile={Boolean(selectedFile)}
								onClose={closeDetails}
							>
								{detail}
							</FilesInspector>
						)}
					</AnimatePresence>
				)}
			</div>

			{deleteTarget && (
				<DeleteConfirmation
					target={deleteTarget}
					onClose={() => setDeleteTarget(null)}
					onRestoreFocus={() => {
						explorerRef.current?.focus({ preventScroll: true });
					}}
					onDeleted={(target) => {
						if (
							target.kind === "file" &&
							target.location === location &&
							target.scope === scope &&
							target.path === selectedFile
						) {
							setSelectedFile(null);
							setDetailOpen(false);
						}
						toast.success(
							target.kind === "file"
								? "File deleted"
								: "File policy deleted",
						);
						refreshFiles();
					}}
				/>
			)}

			<NewShareDialog
				open={newShareOpen}
				onOpenChange={setNewShareOpen}
				scope={scope}
				onCreated={(loc) => {
					refreshFiles();
					handleSelect(loc, "");
				}}
			/>
			<TestAccessModal
				open={testOpen}
				onOpenChange={setTestOpen}
				location={modalTarget.location}
				scope={scope}
				path={modalTarget.path}
			/>
			<PolicyEditorModal
				open={policyOpen}
				onOpenChange={setPolicyOpen}
				location={modalTarget.location}
				scope={scope}
				path={modalTarget.path}
				onSaved={refreshFiles}
			/>
		</div>
	);
}
