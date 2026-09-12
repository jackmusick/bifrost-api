/**
 * Knowledge Management Page
 *
 * Contained document workspace with org/namespace filters, embedded editing,
 * bulk scope changes, import/export, deletion, and pagination.
 */

import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence } from "framer-motion";
import {
	AlertCircle,
	ArrowRightLeft,
	Download,
	FileText,
	Loader2,
	Plus,
	RefreshCw,
	Upload,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { PaginationFooter } from "@/components/pagination/PaginationFooter";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { SearchBox } from "@/components/search/SearchBox";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { ListToolbar } from "@/components/layout/ListToolbar";
import { PageWorkspace } from "@/components/layout/PageWorkspace";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { useAuth } from "@/contexts/AuthContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useOrganizations } from "@/hooks/useOrganizations";
import { toast } from "sonner";
import { authFetch } from "@/lib/api-client";
import { KnowledgeDocumentDrawer } from "@/components/knowledge/KnowledgeDocumentDrawer";
import { exportEntities } from "@/services/exportImport";
import { ImportDialog } from "@/components/ImportDialog";
import { cn } from "@/lib/utils";
import type { RefObject } from "react";

import { KnowledgeFilters } from "./knowledge/KnowledgeFilters";
import { KnowledgeScopeDialog } from "./knowledge/KnowledgeScopeDialog";
import { KnowledgeDeleteDialog } from "./knowledge/KnowledgeDeleteDialog";
import { KnowledgeEditorPane } from "./knowledge/KnowledgeEditorPane";
import {
	KnowledgeDocumentList,
	type DocumentSummary,
} from "./knowledge/KnowledgeDocumentList";

const PAGE_SIZE = 50;

interface KnowledgeNamespace {
	namespace: string;
	document_count: number;
}

async function readResponseDetail(
	response: Response,
	fallback: string,
): Promise<string> {
	try {
		const body = await response.json();
		const detail = body?.detail;
		if (typeof detail === "string") return detail;
		if (typeof detail === "object" && detail) {
			return detail.message || fallback;
		}
		return fallback;
	} catch {
		return fallback;
	}
}

function KnowledgePagination({
	page,
	hasMore,
	onPageChange,
}: {
	page: number;
	hasMore: boolean;
	onPageChange: (page: number) => void;
}) {
	return (
		<PaginationFooter
			aria-label="Knowledge documents pagination"
			summary={`Page ${page + 1}`}
			previousDisabled={page === 0}
			nextDisabled={!hasMore}
			onPrevious={() => onPageChange(Math.max(0, page - 1))}
			onNext={() => onPageChange(page + 1)}
		/>
	);
}

function KnowledgeToolbarActions({
	isPlatformAdmin,
	selectionMode,
	selectedCount,
	isExporting,
	isRefreshing,
	busy,
	onToggleSelectionMode,
	onChangeScope,
	onExport,
	onImport,
	onRefresh,
	onCreate,
	createRef,
}: {
	isPlatformAdmin: boolean;
	selectionMode: boolean;
	selectedCount: number;
	isExporting: boolean;
	isRefreshing: boolean;
	busy: boolean;
	onToggleSelectionMode: () => void;
	onChangeScope: () => void;
	onExport: () => void;
	onImport: () => void;
	onRefresh: () => void;
	onCreate: () => void;
	createRef: RefObject<HTMLButtonElement | null>;
}) {
	return (
		<div className="flex min-w-0 flex-wrap items-center gap-2 sm:ml-auto">
			{isPlatformAdmin && (
				<>
					<Button
						type="button"
						variant={selectionMode ? "secondary" : "outline"}
						className="h-10"
						onClick={onToggleSelectionMode}
						disabled={busy}
					>
						{selectionMode ? "Done" : "Select"}
					</Button>
					{selectionMode && selectedCount > 0 && (
						<>
							<Button
								variant="outline"
								className="h-10"
								onClick={onChangeScope}
								disabled={busy}
							>
								<ArrowRightLeft className="size-4" />
								Change Scope
							</Button>
						</>
					)}
				</>
			)}
			<RecordActionsMenu label="Knowledge actions">
				<DropdownMenuItem
					onSelect={onRefresh}
					disabled={busy || isRefreshing}
				>
					<RefreshCw className="size-4" />
					Refresh
				</DropdownMenuItem>
				{isPlatformAdmin && (
					<>
						<DropdownMenuItem
							onSelect={onExport}
							disabled={busy || isExporting}
						>
							<Download className="size-4" />
							{selectedCount > 0
								? `Export (${selectedCount})`
								: "Export"}
						</DropdownMenuItem>
						<DropdownMenuItem onSelect={onImport} disabled={busy}>
							<Upload className="size-4" />
							Import
						</DropdownMenuItem>
					</>
				)}
			</RecordActionsMenu>

			<Button
				className="h-10"
				ref={createRef}
				onClick={onCreate}
				disabled={busy}
			>
				<Plus className="size-4" />
				Add Document
			</Button>
		</div>
	);
}

function KnowledgeLoadingRows() {
	return (
		<div
			role="status"
			aria-label="Loading documents"
			className="space-y-2 p-3"
		>
			{[...Array(6)].map((_, index) => (
				<Skeleton key={index} className="h-16 w-full" />
			))}
		</div>
	);
}

function KnowledgeEmptyState({
	page,
	onCreate,
	onFirstPage,
}: {
	page: number;
	onCreate: () => void;
	onFirstPage: () => void;
}) {
	return (
		<div className="flex min-h-[22rem] flex-1 flex-col items-center justify-center px-6 py-12 text-center">
			<FileText className="size-12 text-muted-foreground" />
			<h3 className="mt-4 text-lg font-semibold">
				{page > 0 ? "No more documents" : "No documents found"}
			</h3>
			<p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
				{page > 0
					? "You've reached the end of the results."
					: "Add documents to knowledge namespaces for AI agent RAG."}
			</p>
			<Button
				variant="outline"
				onClick={page > 0 ? onFirstPage : onCreate}
				className="mt-4"
			>
				{page > 0 ? (
					"Back to first page"
				) : (
					<>
						<Plus className="size-4" />
						Add Document
					</>
				)}
			</Button>
		</div>
	);
}

export function Knowledge() {
	const { isPlatformAdmin } = useAuth();
	const compactFilters = useMediaQuery("(max-width: 767px)");
	const inlineEditor = useMediaQuery("(min-width: 1280px)");
	const [searchTerm, setSearchTerm] = useState("");
	const [filterOrgId, setFilterOrgId] = useState<string | null | undefined>(
		undefined,
	);
	const [filterNamespace, setFilterNamespace] = useState<string | undefined>(
		undefined,
	);
	const [page, setPage] = useState(0);
	const [deleteDoc, setDeleteDoc] = useState<DocumentSummary | null>(null);
	const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
	const createRef = useRef<HTMLButtonElement>(null);
	const [viewDocId, setViewDocId] = useState<string | null>(null);
	const [viewDocNamespace, setViewDocNamespace] = useState<string>("");
	const [isCreating, setIsCreating] = useState(false);
	const [editorBusy, setEditorBusy] = useState(false);
	const [selectionMode, setSelectionMode] = useState(false);
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [bulkScopeIds, setBulkScopeIds] = useState<string[] | null>(null);
	const [isImportOpen, setIsImportOpen] = useState(false);
	const [isExporting, setIsExporting] = useState(false);

	const { data: organizations } = useOrganizations({
		enabled: isPlatformAdmin,
	});

	const getOrgName = (orgId: string | null | undefined): string => {
		if (!orgId) return "Global";
		const org = organizations?.find((o) => o.id === orgId);
		return org?.name || orgId;
	};

	const filtersKey = JSON.stringify([
		searchTerm,
		filterNamespace,
		filterOrgId === undefined ? "__ALL__" : filterOrgId,
	]);
	const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey);
	if (prevFiltersKey !== filtersKey) {
		setPrevFiltersKey(filtersKey);
		setPage(0);
	}

	const namespaceQuery = useQuery({
		queryKey: ["knowledge", "namespaces"],
		queryFn: async ({ signal }): Promise<KnowledgeNamespace[]> => {
			const response = await authFetch("/api/knowledge-sources", {
				signal,
			});
			if (!response.ok) throw new Error("Could not load namespaces");
			return response.json();
		},
		retry: false,
	});
	const documentQuery = useQuery({
		queryKey: ["knowledge", "documents", filtersKey, page],
		queryFn: async ({ signal }): Promise<DocumentSummary[]> => {
			const params = new URLSearchParams();
			if (searchTerm) params.set("search", searchTerm);
			if (filterNamespace) params.set("namespace", filterNamespace);
			if (filterOrgId === null) params.set("scope", "global");
			else if (filterOrgId !== undefined)
				params.set("scope", filterOrgId);
			params.set("limit", String(PAGE_SIZE));
			params.set("offset", String(page * PAGE_SIZE));
			const response = await authFetch(
				`/api/knowledge-sources/documents?${params}`,
				{ signal },
			);
			if (!response.ok) throw new Error("Could not load documents");
			return response.json();
		},
		placeholderData: (previousData, previousQuery) => {
			const previousKey = previousQuery?.queryKey as
				unknown[] | undefined;
			return previousKey?.[2] === filtersKey ? previousData : undefined;
		},
		retry: false,
	});
	const documents = documentQuery.data ?? [];
	const namespaces = namespaceQuery.data ?? [];
	const isInitialLoading = documentQuery.isPending && !documentQuery.data;
	const hasMore = documents.length === PAGE_SIZE;
	const fetchDocuments = () => documentQuery.refetch();
	const fetchNamespaces = () => namespaceQuery.refetch();
	const editorOpen = Boolean(viewDocId || isCreating);
	const externalBusy = editorBusy;

	const handleDelete = async () => {
		if (!deleteDoc) return;
		const response = await authFetch(
			`/api/knowledge-sources/${encodeURIComponent(deleteDoc.namespace)}/documents/${deleteDoc.id}`,
			{ method: "DELETE" },
		);
		if (!response.ok)
			throw new Error(
				await readResponseDetail(response, "Failed to delete document"),
			);
		toast.success("Document deleted");
		setIsDeleteDialogOpen(false);
		setDeleteDoc(null);
		if (viewDocId === deleteDoc.id) {
			setViewDocId(null);
			setViewDocNamespace("");
		}
		void fetchDocuments();
	};
	const handleDeleteRequest = (doc: DocumentSummary) => {
		setDeleteDoc(doc);
		setIsDeleteDialogOpen(true);
	};

	const openDocument = (doc: DocumentSummary) => {
		if (externalBusy) return;
		setIsCreating(false);
		setViewDocNamespace(doc.namespace);
		setViewDocId(doc.id);
	};

	const closeEditor = (force = false) => {
		if (editorBusy && !force) return;
		setEditorBusy(false);
		setViewDocId(null);
		setViewDocNamespace("");
		setIsCreating(false);
		void fetchDocuments();
		void fetchNamespaces();
	};

	const toggleSelect = (id: string) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	const allVisibleSelected =
		documents.length > 0 &&
		documents.every((doc) => selectedIds.has(doc.id));
	const someVisibleSelected = documents.some((doc) =>
		selectedIds.has(doc.id),
	);
	const toggleSelectAll = () => {
		setSelectedIds((previous) => {
			const next = new Set(previous);
			for (const doc of documents) {
				if (allVisibleSelected) next.delete(doc.id);
				else next.add(doc.id);
			}
			return next;
		});
	};

	const handleExport = async () => {
		const ids = selectedIds.size > 0 ? Array.from(selectedIds) : [];
		setIsExporting(true);
		try {
			await exportEntities("knowledge", ids);
			toast.success("Export downloaded");
		} catch {
			toast.error("Export failed");
		} finally {
			setIsExporting(false);
		}
	};

	return (
		<PageWorkspace className="mx-auto w-full max-w-[1600px] gap-4">
			<ListPageHeader
				className="shrink-0"
				title="Knowledge"
				description="Manage knowledge documents for AI agents."
			/>

			<div className="min-h-0 flex-1 overflow-hidden rounded-[var(--bf-radius-feature)] border border-border/70 bg-card shadow-sm">
				<ListToolbar className="shrink-0 border-b border-border/70 bg-card/95 p-3">
					<KnowledgeFilters
						compact={compactFilters}
						activeCount={
							Number(filterNamespace !== undefined) +
							Number(filterOrgId !== undefined)
						}
						search={
							<SearchBox
								value={searchTerm}
								onChange={setSearchTerm}
								placeholder="Search documents..."
								className="w-full sm:w-72"
								aria-label="Search documents"
							/>
						}
					>
						<Select
							value={filterNamespace ?? "__ALL__"}
							onValueChange={(v) =>
								setFilterNamespace(
									v === "__ALL__" ? undefined : v,
								)
							}
							disabled={externalBusy}
						>
							<SelectTrigger
								aria-label="Filter by namespace"
								className="min-h-10 w-full sm:w-40"
							>
								<SelectValue placeholder="All namespaces" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="__ALL__">
									All namespaces
								</SelectItem>
								{namespaces.map((ns) => (
									<SelectItem
										key={ns.namespace}
										value={ns.namespace}
									>
										{ns.namespace}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
						{isPlatformAdmin && (
							<div className="w-full sm:w-48">
								<OrganizationSelect
									value={filterOrgId}
									onChange={setFilterOrgId}
									showAll={true}
									showGlobal={true}
									placeholder="All organizations"
									disabled={externalBusy}
								/>
							</div>
						)}
					</KnowledgeFilters>
					<KnowledgeToolbarActions
						isPlatformAdmin={isPlatformAdmin}
						selectionMode={selectionMode}
						selectedCount={selectedIds.size}
						isExporting={isExporting}
						isRefreshing={
							documentQuery.isFetching ||
							namespaceQuery.isFetching
						}
						busy={externalBusy}
						onToggleSelectionMode={() => {
							setSelectionMode((value) => !value);
							if (selectionMode) setSelectedIds(new Set());
						}}
						onChangeScope={() =>
							setBulkScopeIds(Array.from(selectedIds))
						}
						onExport={() => void handleExport()}
						onImport={() => setIsImportOpen(true)}
						onRefresh={() => {
							void fetchDocuments();
							void fetchNamespaces();
						}}
						onCreate={() => {
							if (externalBusy) return;
							setViewDocId(null);
							setViewDocNamespace("");
							setIsCreating(true);
						}}
						createRef={createRef}
					/>
				</ListToolbar>

				{namespaceQuery.isError && (
					<Alert className="m-3 w-auto">
						<AlertTitle>
							Namespace filters could not be updated
						</AlertTitle>
						<AlertDescription>
							<p>
								You can still search documents or try loading
								the filters again.
							</p>
							<Button
								variant="outline"
								className="mt-3 min-h-11"
								onClick={() => void fetchNamespaces()}
							>
								Retry namespace filters
							</Button>
						</AlertDescription>
					</Alert>
				)}
				{documentQuery.isError && (
					<Alert variant="destructive" className="m-3 w-auto">
						<AlertCircle className="size-4" />
						<AlertTitle>Documents could not be loaded</AlertTitle>
						<AlertDescription>
							<p>
								{documentQuery.data
									? "Showing the last loaded documents. Your selection is preserved."
									: "Try again to load documents for these filters."}
							</p>
							<Button
								variant="outline"
								className="mt-3 min-h-11"
								onClick={() => void fetchDocuments()}
							>
								Retry documents
							</Button>
						</AlertDescription>
					</Alert>
				)}
				{documentQuery.isFetching && !isInitialLoading && (
					<p
						role="status"
						className="flex shrink-0 items-center gap-2 border-b border-border/70 px-3 py-2 text-sm text-muted-foreground"
					>
						<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						Updating documents...
					</p>
				)}

				<div className="relative flex min-h-[32rem] flex-1 overflow-hidden lg:min-h-0">
					<div
						className={cn(
							"flex min-h-0 min-w-0 flex-1 flex-col",
							editorOpen &&
								!inlineEditor &&
								"invisible pointer-events-none",
						)}
					>
						{isInitialLoading ? (
							<KnowledgeLoadingRows />
						) : documents.length > 0 ? (
							<>
								<KnowledgeDocumentList
									documents={documents}
									selectedDocId={viewDocId}
									selectionMode={selectionMode}
									isPlatformAdmin={isPlatformAdmin}
									selectedIds={selectedIds}
									allVisibleSelected={allVisibleSelected}
									someVisibleSelected={someVisibleSelected}
									getOrgName={getOrgName}
									busy={externalBusy}
									onToggleSelect={toggleSelect}
									onToggleSelectAll={toggleSelectAll}
									onOpen={openDocument}
									onDelete={handleDeleteRequest}
								/>
								{(page > 0 || hasMore) && (
									<div className="shrink-0 border-t border-border/70">
										<KnowledgePagination
											page={page}
											hasMore={hasMore}
											onPageChange={setPage}
										/>
									</div>
								)}
							</>
						) : documentQuery.isError ? null : (
							<KnowledgeEmptyState
								page={page}
								onFirstPage={() => setPage(0)}
								onCreate={() => setIsCreating(true)}
							/>
						)}
					</div>

					<AnimatePresence initial={false}>
						{editorOpen && (
							<KnowledgeEditorPane
								key="knowledge-editor"
								open={editorOpen}
								inline={inlineEditor}
								busy={editorBusy}
								onClose={() => closeEditor()}
							>
								<KnowledgeDocumentDrawer
									returnFocusRef={createRef}
									namespace={viewDocNamespace}
									documentId={viewDocId}
									isCreating={isCreating}
									onClose={() => closeEditor(true)}
									embedded
									onBusyChange={setEditorBusy}
								/>
							</KnowledgeEditorPane>
						)}
					</AnimatePresence>
				</div>
			</div>

			{isDeleteDialogOpen && deleteDoc && (
				<KnowledgeDeleteDialog
					name={deleteDoc.key || deleteDoc.id}
					onConfirm={handleDelete}
					returnFocusRef={createRef}
					onOpenChange={(open) => {
						if (!open) {
							setIsDeleteDialogOpen(false);
							setDeleteDoc(null);
						}
					}}
				/>
			)}

			{bulkScopeIds && (
				<KnowledgeScopeDialog
					documentIds={bulkScopeIds}
					returnFocusRef={createRef}
					onClose={() => setBulkScopeIds(null)}
					onSaved={(updated) => {
						toast.success(`Updated scope for ${updated} documents`);
						setSelectedIds(new Set());
						setSelectionMode(false);
						void fetchDocuments();
					}}
				/>
			)}

			<ImportDialog
				open={isImportOpen}
				onOpenChange={setIsImportOpen}
				entityType="knowledge"
				onImportComplete={() => fetchDocuments()}
			/>
		</PageWorkspace>
	);
}

export default Knowledge;
