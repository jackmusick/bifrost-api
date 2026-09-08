/**
 * Knowledge Management Page
 *
 * Flat document list across all namespaces with org/namespace filters.
 * Supports multi-select for bulk scope changes and pagination.
 */

import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
	RefreshCw,
	BookOpen,
	FileText,
	Plus,
	Trash2,
	Globe,
	Building2,
	ArrowRightLeft,
	Download,
	Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableFooter,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import {
	Pagination,
	PaginationContent,
	PaginationItem,
	PaginationLink,
	PaginationNext,
	PaginationPrevious,
} from "@/components/ui/pagination";
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
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { useAuth } from "@/contexts/AuthContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useOrganizations } from "@/hooks/useOrganizations";
import { toast } from "sonner";
import { authFetch } from "@/lib/api-client";
import { KnowledgeDocumentDrawer } from "@/components/knowledge/KnowledgeDocumentDrawer";
import { exportEntities } from "@/services/exportImport";
import { ImportDialog } from "@/components/ImportDialog";

import { KnowledgeFilters } from "./knowledge/KnowledgeFilters";
import { KnowledgeScopeDialog } from "./knowledge/KnowledgeScopeDialog";
import { KnowledgeDeleteDialog } from "./knowledge/KnowledgeDeleteDialog";

const PAGE_SIZE = 50;

interface DocumentSummary {
	id: string;
	namespace: string;
	key: string | null;
	content_preview: string;
	metadata: Record<string, unknown>;
	organization_id: string | null;
	created_at: string | null;
}

interface KnowledgeNamespace {
	namespace: string;
	document_count: number;
}

function formatKnowledgeDate(value: string | null): string {
	return value ? new Date(value).toLocaleDateString() : "-";
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

function KnowledgeDocumentScopeBadge({
	organizationId,
	getOrgName,
}: {
	organizationId: string | null;
	getOrgName: (orgId: string | null | undefined) => string;
}) {
	if (organizationId) {
		return (
			<Badge
				variant="outline"
				className="h-auto min-h-5 max-w-full whitespace-normal text-xs leading-4 [overflow-wrap:anywhere]"
			>
				<Building2 className="mr-1 h-3 w-3" />
				{getOrgName(organizationId)}
			</Badge>
		);
	}

	return (
		<Badge
			variant="outline"
			className="h-auto min-h-5 max-w-full whitespace-normal text-xs leading-4 [overflow-wrap:anywhere]"
		>
			<Globe className="mr-1 h-3 w-3" />
			Global
		</Badge>
	);
}

function KnowledgeMobileRecord({
	doc,
	isPlatformAdmin,
	isSelected,
	getOrgName,
	onToggleSelect,
	onOpen,
	onDelete,
}: {
	doc: DocumentSummary;
	isPlatformAdmin: boolean;
	isSelected: boolean;
	getOrgName: (orgId: string | null | undefined) => string;
	onToggleSelect: (id: string) => void;
	onOpen: (doc: DocumentSummary) => void;
	onDelete: (doc: DocumentSummary) => void;
}) {
	const titleId = `knowledge-doc-${doc.id}-title`;
	const identityLabel = doc.key || doc.id;
	const actions = (
		<RecordActionsMenu label={`More actions for ${identityLabel}`}>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11 whitespace-nowrap px-3"
				onClick={() => onDelete(doc)}
			>
				<Trash2 className="mr-2 h-4 w-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);

	return (
		<li>
			<Card className="border-border/70 bg-card shadow-none">
				<CardContent className="space-y-4 p-4">
					<article aria-labelledby={titleId} className="space-y-4">
						<div className="flex items-start gap-3">
							{isPlatformAdmin ? (
								<label
									className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] "
									onClick={(e) => e.stopPropagation()}
								>
									<span className="sr-only">
										{`Select ${identityLabel}`}
									</span>
									<Checkbox
										checked={isSelected}
										onCheckedChange={() =>
											onToggleSelect(doc.id)
										}
										onClick={(e) => e.stopPropagation()}
										className="size-5"
									/>
								</label>
							) : null}

							<div className="min-w-0 flex-1">
								<h3
									id={titleId}
									className="text-base font-semibold leading-6"
								>
									<button
										type="button"
										className="min-h-11 text-left [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring"
										onClick={() => onOpen(doc)}
									>
										{identityLabel}
									</button>
								</h3>
							</div>

							{actions}
						</div>

						<dl className="grid grid-cols-2 gap-x-4 gap-y-3">
							<div className="min-w-0">
								<dt className="text-xs leading-5 text-muted-foreground">
									Namespace
								</dt>
								<dd className="min-w-0 text-sm font-medium [overflow-wrap:anywhere]">
									{doc.namespace}
								</dd>
							</div>
							<div className="min-w-0">
								<dt className="text-xs leading-5 text-muted-foreground">
									Scope
								</dt>
								<dd className="min-w-0">
									<KnowledgeDocumentScopeBadge
										organizationId={doc.organization_id}
										getOrgName={getOrgName}
									/>
								</dd>
							</div>
							<div className="col-span-2 min-w-0">
								<dt className="text-xs leading-5 text-muted-foreground">
									Content preview
								</dt>
								<dd className="mt-0.5 min-w-0 text-sm leading-6 text-foreground/90 [overflow-wrap:anywhere]">
									{doc.content_preview}
								</dd>
							</div>
							<div className="min-w-0">
								<dt className="text-xs leading-5 text-muted-foreground">
									Created
								</dt>
								<dd className="min-w-0 text-sm font-medium text-foreground/90">
									{formatKnowledgeDate(doc.created_at)}
								</dd>
							</div>
						</dl>
					</article>
				</CardContent>
			</Card>
		</li>
	);
}

function KnowledgeMobileList({
	documents,
	isPlatformAdmin,
	selectedIds,
	getOrgName,
	onToggleSelect,
	onToggleSelectAll,
	onOpen,
	onDelete,
	page,
	hasMore,
	onPageChange,
}: {
	documents: DocumentSummary[];
	isPlatformAdmin: boolean;
	selectedIds: Set<string>;
	getOrgName: (orgId: string | null | undefined) => string;
	onToggleSelect: (id: string) => void;
	onToggleSelectAll: () => void;
	onOpen: (doc: DocumentSummary) => void;
	onDelete: (doc: DocumentSummary) => void;
	page: number;
	hasMore: boolean;
	onPageChange: (page: number) => void;
}) {
	return (
		<section className="space-y-3 lg:hidden">
			{isPlatformAdmin && (
				<div className="flex items-center justify-between gap-3">
					<p className="text-sm text-muted-foreground">
						{selectedIds.size > 0
							? `${selectedIds.size} selected`
							: "Select documents for bulk changes"}
					</p>
					<Button
						type="button"
						variant="outline"
						className="h-11"
						onClick={onToggleSelectAll}
					>
						{documents.length > 0 &&
						documents.every((doc) => selectedIds.has(doc.id))
							? "Clear all"
							: "Select all"}
					</Button>
				</div>
			)}
			<ul aria-label="Knowledge documents" className="space-y-3">
				{documents.map((doc) => (
					<KnowledgeMobileRecord
						key={doc.id}
						doc={doc}
						isPlatformAdmin={isPlatformAdmin}
						isSelected={selectedIds.has(doc.id)}
						getOrgName={getOrgName}
						onToggleSelect={onToggleSelect}
						onOpen={onOpen}
						onDelete={onDelete}
					/>
				))}
			</ul>
			{(page > 0 || hasMore) && (
				<div className="pt-1">
					<Pagination>
						<PaginationContent>
							<PaginationItem>
								<PaginationPrevious
									href="#"
									onClick={(e) => {
										e.preventDefault();
										if (page > 0) onPageChange(page - 1);
									}}
									className={
										page === 0
											? "min-h-11 min-w-11 pointer-events-none opacity-50"
											: "min-h-11 min-w-11 cursor-pointer"
									}
									aria-disabled={page === 0}
								/>
							</PaginationItem>
							<PaginationItem>
								<PaginationLink isActive>
									{page + 1}
								</PaginationLink>
							</PaginationItem>
							<PaginationItem>
								<PaginationNext
									href="#"
									onClick={(e) => {
										e.preventDefault();
										if (hasMore) onPageChange(page + 1);
									}}
									className={
										!hasMore
											? "min-h-11 min-w-11 pointer-events-none opacity-50"
											: "min-h-11 min-w-11 cursor-pointer"
									}
									aria-disabled={!hasMore}
								/>
							</PaginationItem>
						</PaginationContent>
					</Pagination>
				</div>
			)}
		</section>
	);
}

export function Knowledge() {
	const { isPlatformAdmin } = useAuth();
	const compactLayout = useMediaQuery("(max-width: 1023px)");
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

	// Keep all-scopes and global distinct, including when resetting pagination.
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
		retry: false,
	});
	const documents = documentQuery.data ?? [];
	const namespaces = namespaceQuery.data ?? [];
	const isLoading = documentQuery.isPending;
	const hasMore = documents.length === PAGE_SIZE;
	const fetchDocuments = () => documentQuery.refetch();
	const fetchNamespaces = () => namespaceQuery.refetch();

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
		void fetchDocuments();
	};
	const handleDeleteRequest = (doc: DocumentSummary) => {
		setDeleteDoc(doc);
		setIsDeleteDialogOpen(true);
	};

	const openDocument = (doc: DocumentSummary) => {
		setViewDocNamespace(doc.namespace);
		setViewDocId(doc.id);
	};

	const toggleSelect = (id: string) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) {
				next.delete(id);
			} else {
				next.add(id);
			}
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
		<div className="h-full flex flex-col space-y-6 max-w-7xl mx-auto">
			<ListPageHeader
				title="Knowledge"
				description="Manage knowledge documents for AI agents"
				actions={
					<>
						<Button
							variant="outline"
							size="icon-lg"
							className="h-11 w-11"
							onClick={() => {
								void fetchDocuments();
								void fetchNamespaces();
							}}
							disabled={
								documentQuery.isFetching ||
								namespaceQuery.isFetching
							}
							title="Refresh"
						>
							<RefreshCw className="h-4 w-4" />
						</Button>
						<Button
							className="h-11"
							ref={createRef}
							onClick={() => setIsCreating(true)}
						>
							<Plus className="h-4 w-4 mr-1" />
							Add Document
						</Button>
					</>
				}
			/>

			<ListToolbar>
				<KnowledgeFilters
					compact={compactLayout}
					activeCount={
						Number(filterNamespace !== undefined) +
						Number(filterOrgId !== undefined)
					}
					search={
						<SearchBox
							value={searchTerm}
							onChange={setSearchTerm}
							placeholder={
								compactLayout
									? "Search…"
									: "Search documents..."
							}
							className="w-full sm:flex-1"
							aria-label="Search documents"
						/>
					}
				>
					<Select
						value={filterNamespace ?? "__ALL__"}
						onValueChange={(v) =>
							setFilterNamespace(v === "__ALL__" ? undefined : v)
						}
					>
						<SelectTrigger
							aria-label="Filter by namespace"
							className="min-h-11 w-full sm:w-48"
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
						<div className="w-full sm:w-64">
							<OrganizationSelect
								value={filterOrgId}
								onChange={setFilterOrgId}
								showAll={true}
								showGlobal={true}
								placeholder="All organizations"
							/>
						</div>
					)}
				</KnowledgeFilters>
				{isPlatformAdmin && (
					<div className="flex flex-wrap items-center gap-2 sm:ml-auto">
						{selectedIds.size > 0 && (
							<>
								<span className="text-sm text-muted-foreground">
									{selectedIds.size} selected
								</span>
								<Button
									variant="outline"
									className="h-11"
									onClick={() => {
										setBulkScopeIds(
											Array.from(selectedIds),
										);
									}}
								>
									<ArrowRightLeft className="h-4 w-4 mr-1" />
									Change Scope
								</Button>
							</>
						)}
						<Button
							variant="outline"
							className="h-11"
							onClick={handleExport}
							disabled={isExporting}
						>
							<Download className="h-4 w-4 mr-1" />
							{selectedIds.size > 0
								? `Export (${selectedIds.size})`
								: "Export All"}
						</Button>
						<Button
							variant="outline"
							className="h-11"
							onClick={() => setIsImportOpen(true)}
						>
							<Upload className="h-4 w-4 mr-1" />
							Import
						</Button>
					</div>
				)}
			</ListToolbar>

			{namespaceQuery.isError && (
				<Alert>
					<AlertTitle>
						Namespace filters could not be updated
					</AlertTitle>
					<AlertDescription>
						<p>
							You can still search documents or try loading the
							filters again.
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
				<Alert variant="destructive">
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
			{documentQuery.isFetching && !isLoading && (
				<p role="status" className="text-sm text-muted-foreground">
					Updating documents…
				</p>
			)}
			{/* Content */}
			{isLoading ? (
				<div
					role="status"
					aria-label="Loading documents"
					className="space-y-2"
				>
					{[...Array(5)].map((_, i) => (
						<Skeleton key={i} className="h-12 w-full" />
					))}
				</div>
			) : documents.length > 0 ? (
				compactLayout ? (
					<KnowledgeMobileList
						documents={documents}
						isPlatformAdmin={isPlatformAdmin}
						selectedIds={selectedIds}
						getOrgName={getOrgName}
						onToggleSelect={toggleSelect}
						onToggleSelectAll={toggleSelectAll}
						onOpen={openDocument}
						onDelete={handleDeleteRequest}
						page={page}
						hasMore={hasMore}
						onPageChange={setPage}
					/>
				) : (
					<div className="flex-1 min-h-0 flex flex-col">
						<div className="flex-1 min-h-0">
							<DataTable className="max-h-full">
								<DataTableHeader>
									<DataTableRow>
										{isPlatformAdmin && (
											<DataTableHead className="w-10">
												<Checkbox
													aria-label="Select visible documents"
													checked={
														allVisibleSelected
															? true
															: someVisibleSelected
																? "indeterminate"
																: false
													}
													onCheckedChange={
														toggleSelectAll
													}
												/>
											</DataTableHead>
										)}
										<DataTableHead className="w-0 whitespace-nowrap">
											Scope
										</DataTableHead>
										<DataTableHead className="w-0 whitespace-nowrap">
											Namespace
										</DataTableHead>
										<DataTableHead>Key</DataTableHead>
										<DataTableHead className="w-0 whitespace-nowrap">
											Created
										</DataTableHead>
										<DataTableHead className="w-0 whitespace-nowrap text-right" />
									</DataTableRow>
								</DataTableHeader>
								<DataTableBody>
									{documents.map((doc) => (
										<DataTableRow
											key={doc.id}
											clickable
											onClick={() => openDocument(doc)}
										>
											{isPlatformAdmin && (
												<DataTableCell>
													<Checkbox
														aria-label={`Select ${doc.key || doc.id}`}
														checked={selectedIds.has(
															doc.id,
														)}
														onCheckedChange={() =>
															toggleSelect(doc.id)
														}
														onClick={(e) =>
															e.stopPropagation()
														}
													/>
												</DataTableCell>
											)}
											<DataTableCell className="w-0 whitespace-nowrap">
												<KnowledgeDocumentScopeBadge
													organizationId={
														doc.organization_id
													}
													getOrgName={getOrgName}
												/>
											</DataTableCell>
											<DataTableCell className="w-0 whitespace-nowrap">
												<div className="flex items-center gap-2">
													<BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
													{doc.namespace}
												</div>
											</DataTableCell>
											<DataTableCell className="font-mono text-xs">
												<button
													type="button"
													className="min-h-11 text-left [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring"
													onClick={(event) => {
														event.stopPropagation();
														openDocument(doc);
													}}
												>
													{doc.key || doc.id}
												</button>
											</DataTableCell>
											<DataTableCell className="w-0 whitespace-nowrap text-xs text-muted-foreground">
												{formatKnowledgeDate(
													doc.created_at,
												)}
											</DataTableCell>
											<DataTableCell className="w-0 whitespace-nowrap text-right">
												<RecordActionsMenu
													label={`More actions for ${doc.key || doc.id}`}
												>
													<DropdownMenuItem
														variant="destructive"
														className="min-h-11 whitespace-nowrap px-3"
														onClick={(e) => {
															e.stopPropagation();
															handleDeleteRequest(
																doc,
															);
														}}
													>
														<Trash2 className="mr-2 h-4 w-4" />
														Delete
													</DropdownMenuItem>
												</RecordActionsMenu>
											</DataTableCell>
										</DataTableRow>
									))}
								</DataTableBody>
								{(page > 0 || hasMore) && (
									<DataTableFooter>
										<DataTableRow>
											<DataTableCell
												colSpan={
													isPlatformAdmin ? 6 : 5
												}
												className="p-0"
											>
												<div className="px-6 py-4 flex items-center justify-center">
													<Pagination>
														<PaginationContent>
															<PaginationItem>
																<PaginationPrevious
																	href="#"
																	onClick={(
																		e,
																	) => {
																		e.preventDefault();
																		if (
																			page >
																			0
																		)
																			setPage(
																				page -
																					1,
																			);
																	}}
																	className={
																		page ===
																		0
																			? "min-h-11 min-w-11 pointer-events-none opacity-50"
																			: "min-h-11 min-w-11 cursor-pointer"
																	}
																	aria-disabled={
																		page ===
																		0
																	}
																/>
															</PaginationItem>
															<PaginationItem>
																<PaginationLink
																	isActive
																>
																	{page + 1}
																</PaginationLink>
															</PaginationItem>
															<PaginationItem>
																<PaginationNext
																	href="#"
																	onClick={(
																		e,
																	) => {
																		e.preventDefault();
																		if (
																			hasMore
																		)
																			setPage(
																				page +
																					1,
																			);
																	}}
																	className={
																		!hasMore
																			? "min-h-11 min-w-11 pointer-events-none opacity-50"
																			: "min-h-11 min-w-11 cursor-pointer"
																	}
																	aria-disabled={
																		!hasMore
																	}
																/>
															</PaginationItem>
														</PaginationContent>
													</Pagination>
												</div>
											</DataTableCell>
										</DataTableRow>
									</DataTableFooter>
								)}
							</DataTable>
						</div>
					</div>
				)
			) : documentQuery.isError ? null : (
				<Card>
					<CardContent className="flex flex-col items-center justify-center py-12 text-center">
						<FileText className="h-12 w-12 text-muted-foreground" />
						<h3 className="mt-4 text-lg font-semibold">
							{page > 0
								? "No more documents"
								: "No documents found"}
						</h3>
						<p className="mt-2 text-sm text-muted-foreground">
							{page > 0
								? "You've reached the end of the results."
								: "Add documents to knowledge namespaces for AI agent RAG"}
						</p>
						{page > 0 ? (
							<Button
								variant="outline"
								onClick={() => setPage(0)}
								className="mt-4"
							>
								Back to first page
							</Button>
						) : (
							<Button
								variant="outline"
								onClick={() => setIsCreating(true)}
								className="mt-4"
							>
								<Plus className="h-4 w-4 mr-2" />
								Add Document
							</Button>
						)}
					</CardContent>
				</Card>
			)}

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
						void fetchDocuments();
					}}
				/>
			)}

			{/* Import Dialog */}
			<ImportDialog
				open={isImportOpen}
				onOpenChange={setIsImportOpen}
				entityType="knowledge"
				onImportComplete={() => fetchDocuments()}
			/>

			{/* Document Drawer */}
			<KnowledgeDocumentDrawer
				returnFocusRef={createRef}
				namespace={viewDocNamespace}
				documentId={viewDocId}
				isCreating={isCreating}
				onClose={() => {
					setViewDocId(null);
					setViewDocNamespace("");
					setIsCreating(false);
					fetchDocuments();
					fetchNamespaces();
				}}
			/>
		</div>
	);
}

export default Knowledge;
