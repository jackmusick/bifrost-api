import { useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ChevronLeft, Menu, Plus, Upload } from "lucide-react";
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
import { ShareTree, type ShareTreeAction } from "./ShareTree";
import { TestAccessModal } from "./TestAccessModal";
import { useFileUpload } from "./useFileUpload";

const READ_ONLY_LOCATIONS = new Set(["uploads"]);
const PANE =
	"flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border bg-card";

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
	const [deleteTarget, setDeleteTarget] = useState<FileDeleteTarget | null>(
		null,
	);
	const queryClient = useQueryClient();
	function refreshFiles() {
		void queryClient.invalidateQueries({ queryKey: ["file-structure"] });
		setRefreshKey((key) => key + 1);
	}
	const { data: organizations = [] } = useOrganizations({
		enabled: isPlatformAdmin && !install,
	});
	const isWide = useMediaQuery("(min-width: 1440px)");

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

	function resetTo(nextLocation: string | null, nextPrefix: string) {
		setLocation(nextLocation);
		setPrefix(nextPrefix);
		setSelectedFile(null);
	}

	function handleScopeChange(next: string | null | undefined) {
		setSelectorScope(next ?? null);
		resetTo(null, "");
	}

	function handleSelect(nextLocation: string, nextPrefix: string) {
		resetTo(nextLocation, nextPrefix);
		setTreeOpen(false);
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
		} else if (action === "test") {
			openTest(loc, treePrefix);
		} else if (action === "newPolicy") {
			if (solutionReadOnly) return;
			openPolicy(loc, treePrefix);
		} else if (action === "upload") {
			if (solutionReadOnly) return;
			handleSelect(loc, treePrefix);
		}
	}

	function handleRowAction(action: ListingRowAction, path: string) {
		if (location === null) return;
		if (readOnly && (action === "policy" || action === "delete")) return;
		if (action === "preview") {
			setSelectedFile(path);
			if (!isWide) setDetailOpen(true);
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
		if (!isWide) setDetailOpen(true);
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
	const detail = isWide ? (
		<div className="flex h-full min-h-0 flex-col" data-testid="detail-pane">
			<div className="min-h-0 flex-1 overflow-hidden border-b">
				{preview}
			</div>
			<div className="min-h-0 flex-1 overflow-hidden">{access}</div>
		</div>
	) : (
		<Tabs
			key={selectedFile ?? "access"}
			defaultValue={selectedFile ? "preview" : "access"}
			className="flex h-full min-h-0 flex-col gap-0"
			data-testid="detail-pane"
		>
			<TabsList
				aria-label="File details"
				className="m-3 grid w-[calc(100%-1.5rem)] shrink-0 grid-cols-2 group-data-horizontal/tabs:h-auto"
			>
				<TabsTrigger value="preview" className="min-h-11">
					Preview
				</TabsTrigger>
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

	return (
		<div
			ref={explorerRef}
			tabIndex={-1}
			role="region"
			aria-label="Files explorer"
			className="flex h-full min-h-0 flex-col gap-3 outline-none"
		>
			<header className="flex shrink-0 flex-wrap items-center gap-2">
				<div className="flex w-full min-w-0 flex-wrap items-center gap-2 min-[1440px]:w-auto min-[1440px]:flex-1">
					{install && !embedded && (
						<>
							<Button
								asChild
								variant="outline"
								size="sm"
								className="min-h-11"
							>
								<Link
									to={`/solutions/${install}`}
									data-testid="files-solution-back"
									aria-label="Back to Solution"
								>
									<ChevronLeft data-icon="inline-start" />
									Back
								</Link>
							</Button>
							<span
								className="min-w-0 flex-1 text-sm font-semibold text-foreground [overflow-wrap:anywhere]"
								title={solutionTitle}
							>
								{solutionTitle}
							</span>
						</>
					)}
					{!isWide && (
						<Sheet open={treeOpen} onOpenChange={setTreeOpen}>
							<SheetTrigger asChild>
								<Button
									type="button"
									variant="outline"
									size="icon-lg"
									aria-label="Open shares"
								>
									<Menu className="h-4 w-4" />
								</Button>
							</SheetTrigger>
							<SheetContent side="left" className="w-72 p-0">
								<SheetHeader className="min-h-20 px-4 py-5">
									<SheetTitle>Shares</SheetTitle>
								</SheetHeader>
								<div className="flex min-h-0 flex-1 flex-col">
									{tree}
								</div>
							</SheetContent>
						</Sheet>
					)}
					{isPlatformAdmin && !install && (
						<div className="min-w-0 flex-1 sm:max-w-56">
							<OrganizationSelect
								aria-label="File scope"
								value={selectorScope}
								onChange={handleScopeChange}
								showGlobal
								showAll={false}
							/>
						</div>
					)}
					{view === "browse" && !install && (
						<div className="min-w-0 basis-full min-[1440px]:basis-auto min-[1440px]:flex-1">
							<Breadcrumbs
								scopeLabel={scopeLabel}
								location={location}
								segments={segments}
								onNavigate={handleBreadcrumb}
							/>
						</div>
					)}
					{view === "browse" && install && location !== null && (
						<div className="min-w-0 basis-full min-[1440px]:basis-auto min-[1440px]:flex-1">
							<Breadcrumbs
								scopeLabel={solutionTitle}
								includeScopeRoot={false}
								location={location}
								segments={segments}
								onNavigate={handleBreadcrumb}
							/>
						</div>
					)}
				</div>
				<div className="flex w-full min-w-0 flex-wrap items-center gap-2 min-[1440px]:ml-auto min-[1440px]:w-auto min-[1440px]:shrink-0">
					{!install && (
						<>
							<Tabs
								className="w-full sm:w-auto"
								value={view}
								onValueChange={(value) =>
									setView(value as "browse" | "policies")
								}
							>
								<TabsList className="min-h-11 w-full group-data-horizontal/tabs:h-auto sm:w-auto">
									<TabsTrigger
										className="min-h-11"
										value="browse"
									>
										Browse
									</TabsTrigger>
									<TabsTrigger
										className="min-h-11"
										value="policies"
									>
										Policies
									</TabsTrigger>
								</TabsList>
							</Tabs>
							<Button
								type="button"
								size="sm"
								variant="outline"
								className="min-h-11 flex-1 sm:flex-none"
								onClick={() => setNewShareOpen(true)}
							>
								<Plus className="h-4 w-4" /> New Share
							</Button>
						</>
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
										void uploadFiles(event.target.files);
									event.target.value = "";
								}}
							/>
							<Button
								type="button"
								size="sm"
								className="min-h-11 flex-1 sm:flex-none"
								onClick={() => uploadInputRef.current?.click()}
								disabled={uploading}
							>
								<Upload className="h-4 w-4" />{" "}
								{uploading ? "Uploading…" : "Upload"}
							</Button>
						</>
					)}
				</div>
			</header>
			{uploadProgress && (
				<p
					role="status"
					className="shrink-0 text-sm text-muted-foreground [overflow-wrap:anywhere]"
				>
					{uploadProgress}
				</p>
			)}
			{uploadError && (
				<Alert variant="destructive" className="shrink-0">
					<AlertTitle>Upload failed</AlertTitle>
					<AlertDescription>
						<p className="[overflow-wrap:anywhere]">
							{uploadError}
						</p>
						<Button
							variant="outline"
							className="mt-3 min-h-11"
							disabled={uploading}
							onClick={() => void retryUpload()}
						>
							Retry upload
						</Button>
					</AlertDescription>
				</Alert>
			)}

			{view === "policies" && !install ? (
				<div className="min-h-0 flex-1 overflow-hidden">
					<PoliciesView
						scope={scope}
						refreshKey={refreshKey}
						onEdit={(policy) =>
							openPolicy(policy.location, policy.path)
						}
						onDelete={(policy) => void handleDeletePolicy(policy)}
					/>
				</div>
			) : (
				<div className="grid min-h-0 flex-1 gap-3 overflow-hidden min-[1440px]:grid-cols-[16rem_minmax(0,1fr)_20rem]">
					{isWide && <div className={PANE}>{tree}</div>}
					{/* No PANE here: FolderListing's DataTable is its own card —
					    wrapping it in PANE would nest a card in a card. */}
					<div className="flex min-h-0 flex-col overflow-hidden">
						<FolderListing
							key={`listing-${scope}-${location}-${prefix}`}
							scope={scope}
							location={location}
							prefix={prefix}
							readOnly={readOnly}
							managedBySolution={solutionReadOnly}
							solutionId={install}
							onOpenFolder={(next) => resetTo(location, next)}
							onSelectFile={selectFile}
							onRowAction={handleRowAction}
							onFolderAction={(action, folderPrefix) =>
								location !== null &&
								handleTreeAction(action, location, folderPrefix)
							}
							onUploaded={refreshFiles}
						/>
					</div>
					{isWide && <div className={PANE}>{detail}</div>}
				</div>
			)}

			{!isWide && (
				<Sheet open={detailOpen} onOpenChange={setDetailOpen}>
					<SheetContent
						side="right"
						className="w-full p-0 sm:max-w-md"
					>
						<SheetHeader className="min-h-20 px-4 py-5">
							<SheetTitle>Details</SheetTitle>
						</SheetHeader>
						<div className="flex min-h-0 flex-1 flex-col">
							{detail}
						</div>
					</SheetContent>
				</Sheet>
			)}

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
