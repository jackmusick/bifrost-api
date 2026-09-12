import { useState, useMemo, useRef, useEffect } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import {
	ArrowLeft,
	SlidersHorizontal,
	Plus,
	RefreshCw,
	Database,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageWorkspace } from "@/components/layout/PageWorkspace";
import { useTable, useDocuments, useDeleteDocument } from "@/services/tables";
import { DocumentInspector } from "@/components/tables/DocumentInspector";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TableFilterSidebar } from "@/components/tables/TableFilterSidebar";
import { DocumentRecordList } from "@/components/tables/DocumentRecordList";
import { SearchBox } from "@/components/search/SearchBox";
import { useSearch } from "@/hooks/useSearch";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import type { DocumentPublic } from "@/services/tables";
import { parseSolutionFrom } from "@/lib/solution-back-nav";
import { TableDetailHeader } from "./table-detail/TableDetailHeader";
import { DocumentPagination } from "./table-detail/DocumentPagination";
import { DocumentDeleteDialog } from "./table-detail/DocumentDeleteDialog";
import { DocumentCollectionState } from "./table-detail/DocumentCollectionState";

export function TableDetail() {
	const { tableId = "" } = useParams<{ tableId: string }>();
	return <TableDetailSession key={tableId} tableId={tableId} />;
}

function TableDetailSession({ tableId }: { tableId: string }) {
	const inlineInspector = useMediaQuery("(min-width: 1280px)");
	const reduceMotion = useReducedMotion();
	const frameRef = useRef<HTMLDivElement>(null);
	const [editing, setEditing] = useState(false);
	const [editorBusy, setEditorBusy] = useState(false);
	const { search } = useLocation();
	const fromSolution = parseSolutionFrom(search);
	const backTo = fromSolution ? `/solutions/${fromSolution}` : "/tables";
	const backLabel = fromSolution ? "Back to Solution" : "Back to Tables";
	const [selectedDocument, setSelectedDocument] = useState<DocumentPublic>();
	const [isDialogOpen, setIsDialogOpen] = useState(false);
	const [documentToDelete, setDocumentToDelete] = useState<DocumentPublic>();
	const [pageSize, setPageSize] = useState(25);
	const [currentPage, setCurrentPage] = useState(0);
	const [whereClause, setWhereClause] = useState<Record<string, unknown>>({});
	const [searchTerm, setSearchTerm] = useState("");
	const [sidebarOpen, setSidebarOpen] = useState(false);
	const [filterRevision, setFilterRevision] = useState(0);
	useEffect(() => {
		if (!isDialogOpen || inlineInspector) return;
		const frame = requestAnimationFrame(() =>
			frameRef.current?.scrollIntoView?.({
				block: "start",
				behavior: "instant",
			}),
		);
		return () => cancelAnimationFrame(frame);
	}, [isDialogOpen, inlineInspector]);
	const filterToggle = useRef<HTMLButtonElement>(null);
	const query = useMemo(
		() => ({
			where: Object.keys(whereClause).length ? whereClause : undefined,
			limit: pageSize,
			offset: currentPage * pageSize,
			order_dir: "desc" as const,
		}),
		[whereClause, pageSize, currentPage],
	);
	const tableQuery = useTable(tableId);
	const documentsQuery = useDocuments(tableId, query, {
		preservePageData: true,
	});
	const deleteDocument = useDeleteDocument();
	const table = tableQuery.data;
	const documents = useMemo(
		() => documentsQuery.data?.documents ?? [],
		[documentsQuery.data?.documents],
	);
	const filteredDocuments = useSearch(documents, searchTerm, [
		"id",
		(doc) => JSON.stringify(doc.data),
	]);
	const total = documentsQuery.data?.total ?? 0;
	const hasActiveFilters = Object.keys(whereClause).length > 0;
	const dataColumns = useMemo(
		() =>
			Array.from(
				new Set(documents.flatMap((doc) => Object.keys(doc.data))),
			)
				.sort((a, b) => {
					const priority = (key: string) => {
						if (["name", "title", "label"].includes(key)) return 0;
						const value = documents.find(
							(doc) => doc.data[key] != null,
						)?.data[key];
						return value !== null && typeof value === "object"
							? 2
							: 1;
					};
					return priority(a) - priority(b);
				})
				.slice(0, 3),
		[documents],
	);
	const handleAdd = () => {
		setSelectedDocument(undefined);
		setEditing(true);
		setSidebarOpen(false);
		setIsDialogOpen(true);
	};
	const handleEdit = (doc: DocumentPublic) => {
		if (editorBusy) return;
		setSelectedDocument(doc);
		setEditing(true);
		setSidebarOpen(false);
		setIsDialogOpen(true);
	};
	const handleOpen = (doc: DocumentPublic) => {
		if (editorBusy) return;
		setSelectedDocument(doc);
		setEditing(false);
		setSidebarOpen(false);
		setIsDialogOpen(true);
	};
	const closeInspector = () => {
		setIsDialogOpen(false);
		setSelectedDocument(undefined);
		setEditing(false);
		setEditorBusy(false);
	};
	const handleClearFilters = () => {
		setWhereClause({});
		setCurrentPage(0);
	};
	const clearAll = () => {
		handleClearFilters();
		setSearchTerm("");
		setFilterRevision((value) => value + 1);
	};
	const closeFilters = () => {
		setSidebarOpen(false);
		filterToggle.current?.focus();
	};

	if (!table)
		return (
			<div className="space-y-4">
				<Button
					type="button"
					variant="ghost"
					asChild
					className="min-h-11"
				>
					<Link to={backTo}>
						<ArrowLeft aria-hidden="true" className="size-4" />
						{backLabel}
					</Link>
				</Button>
				<DocumentCollectionState
					headingLevel={1}
					title={
						tableQuery.isError
							? "Table could not be loaded"
							: "Loading table…"
					}
					description={
						tableQuery.isError
							? "Try again to check whether this table is available to you."
							: undefined
					}
					error={tableQuery.isError}
					busy={tableQuery.isFetching}
					action={tableQuery.isError ? "Retry table" : undefined}
					onAction={() => void tableQuery.refetch()}
				/>
			</div>
		);

	return (
		<PageWorkspace className="mx-auto w-full max-w-[1600px] gap-4">
			<TableDetailHeader
				name={table.name}
				description={table.description}
				backTo={backTo}
				backLabel={backLabel}
			/>
			<div
				ref={frameRef}
				className={cn(
					"scroll-mt-4 flex min-h-0 max-h-full flex-col overflow-hidden rounded-[var(--bf-radius-feature)] border border-border/70 bg-card",
					isDialogOpen || sidebarOpen
						? "h-[calc(100dvh-6rem)] lg:h-auto lg:flex-1"
						: "shrink",
				)}
			>
				<div className="flex shrink-0 flex-wrap items-center border-b border-border/70 bg-muted/20">
					<div className="flex h-12 w-full shrink-0 items-center gap-2 border-b px-4 text-sm sm:w-44 sm:border-b-0 sm:border-r">
						<Database className="size-4 text-primary" />
						Documents
					</div>
					<SearchBox
						value={searchTerm}
						onChange={setSearchTerm}
						placeholder="Search This Page..."
						aria-label="Search documents on this page"
						className="min-w-40 flex-1 [&>input]:h-12 [&>input]:rounded-none [&>input]:border-0 [&>input]:bg-transparent [&>input]:shadow-none [&>input]:focus-visible:ring-inset"
					/>
					<div className="flex min-w-0 flex-wrap items-center gap-1 px-3 py-1">
						<Button
							ref={filterToggle}
							variant="ghost"
							disabled={editorBusy || (isDialogOpen && editing)}
							aria-expanded={sidebarOpen}
							aria-controls="document-filters"
							onClick={() => {
								setSidebarOpen(!sidebarOpen);
								if (!sidebarOpen) closeInspector();
							}}
						>
							<SlidersHorizontal className="size-4" />
							Filters
							{hasActiveFilters
								? ` (${Object.keys(whereClause).length})`
								: ""}
						</Button>
						<Button
							variant="ghost"
							size="icon"
							aria-label="Refresh documents"
							title="Refresh"
							aria-busy={documentsQuery.isFetching}
							disabled={documentsQuery.isFetching || editorBusy}
							onClick={() => void documentsQuery.refetch()}
						>
							<RefreshCw
								className={cn(
									"size-4",
									documentsQuery.isFetching &&
										"animate-spin motion-reduce:animate-none",
								)}
							/>
						</Button>
						<Button
							disabled={editorBusy || (isDialogOpen && editing)}
							onClick={handleAdd}
						>
							<Plus className="size-4" />
							Add Document
						</Button>
					</div>
				</div>
				{tableQuery.isError && (
					<DocumentCollectionState
						title="Table details could not be refreshed"
						description="Showing the last available table details."
						error
						busy={tableQuery.isFetching}
						action="Retry table"
						onAction={() => void tableQuery.refetch()}
					/>
				)}
				<div
					className={cn(
						"relative flex min-h-0 min-w-0 flex-col lg:flex-row",
						(isDialogOpen || sidebarOpen) && "flex-1",
					)}
				>
					<div
						id="document-filters"
						hidden={!sidebarOpen}
						className="min-h-0 w-full shrink-0 overflow-auto border-b lg:w-72 lg:border-b-0 lg:border-r"
					>
						<TableFilterSidebar
							key={filterRevision}
							onApplyFilters={(where) => {
								setWhereClause(where);
								setCurrentPage(0);
							}}
							onClearFilters={handleClearFilters}
							hasActiveFilters={hasActiveFilters}
							onClose={closeFilters}
							className="min-h-0 w-full rounded-none border-0"
						/>
					</div>
					<section
						aria-label="Documents"
						className="flex min-h-0 min-w-0 flex-1 flex-col"
						aria-busy={
							documentsQuery.isFetching ? "true" : undefined
						}
						inert={
							isDialogOpen && !inlineInspector ? true : undefined
						}
					>
						{documentsQuery.isError && (
							<DocumentCollectionState
								title="Documents could not be loaded"
								description={
									documentsQuery.data
										? "Showing the last available documents for this query."
										: "Your query is preserved. Try loading it again."
								}
								error
								busy={documentsQuery.isFetching || editorBusy}
								action="Retry documents"
								onAction={() => void documentsQuery.refetch()}
							/>
						)}
						{documentsQuery.isLoading ? (
							<DocumentCollectionState title="Loading documents…" />
						) : (
							<>
								{filteredDocuments.length > 0 ? (
									<DocumentRecordList
										documents={filteredDocuments}
										dataColumns={dataColumns}
										selectedId={selectedDocument?.id}
										onOpen={handleOpen}
										disabled={
											editorBusy ||
											(isDialogOpen && editing)
										}
										onEdit={handleEdit}
										onDelete={setDocumentToDelete}
									/>
								) : (
									!documentsQuery.isError && (
										<DocumentCollectionState
											title={
												searchTerm
													? "No documents match on this page"
													: hasActiveFilters
														? "No documents match your filters"
														: currentPage > 0
															? "No documents on this page"
															: "No documents yet"
											}
											description={
												searchTerm
													? "Try a different search or move to another page."
													: hasActiveFilters
														? "Adjust your query filters to find documents."
														: currentPage > 0
															? "The table may have changed. Return to the previous page."
															: "Add your first document to this table."
											}
											action={
												searchTerm || hasActiveFilters
													? "Clear search and filters"
													: currentPage > 0
														? "Previous page"
														: "Add document"
											}
											onAction={
												searchTerm || hasActiveFilters
													? clearAll
													: currentPage > 0
														? () =>
																setCurrentPage(
																	(page) =>
																		Math.max(
																			0,
																			page -
																				1,
																		),
																)
														: handleAdd
											}
										/>
									)
								)}
								{documentsQuery.data && (
									<DocumentPagination
										page={currentPage}
										pageSize={pageSize}
										total={total}
										busy={
											documentsQuery.isFetching ||
											editorBusy
										}
										onPageChange={setCurrentPage}
										onPageSizeChange={(size) => {
											setPageSize(size);
											setCurrentPage(0);
										}}
									/>
								)}
							</>
						)}
					</section>
					<AnimatePresence initial={false}>
						{isDialogOpen && (
							<motion.aside
								key="record-inspector"
								role="region"
								aria-label="Document inspector"
								className={cn(
									"z-20 flex min-h-0 flex-col overflow-hidden bg-card",
									inlineInspector
										? "relative shrink-0 border-l"
										: "absolute inset-0",
								)}
								initial={
									reduceMotion
										? false
										: inlineInspector
											? { width: 0, opacity: 0 }
											: { x: "100%", opacity: 0 }
								}
								animate={
									inlineInspector
										? {
												width: "min(42vw, 560px)",
												opacity: 1,
											}
										: { width: "100%", x: 0, opacity: 1 }
								}
								exit={
									inlineInspector
										? { width: 0, opacity: 0 }
										: { x: "100%", opacity: 0 }
								}
								transition={{
									duration: reduceMotion ? 0 : 0.2,
									ease: [0.22, 1, 0.36, 1],
								}}
								onKeyDown={(event) => {
									if (
										event.key === "Escape" &&
										!event.defaultPrevented &&
										!editorBusy
									) {
										event.stopPropagation();
										closeInspector();
										filterToggle.current?.focus();
									}
								}}
							>
								<DocumentInspector
									document={selectedDocument}
									tableId={tableId}
									editing={editing}
									onEdit={() => setEditing(true)}
									onClose={closeInspector}
									onBusyChange={setEditorBusy}
									onDelete={
										selectedDocument
											? () =>
													setDocumentToDelete(
														selectedDocument,
													)
											: undefined
									}
								/>
							</motion.aside>
						)}
					</AnimatePresence>
				</div>
			</div>
			{documentToDelete && (
				<DocumentDeleteDialog
					key={documentToDelete.id}
					returnFocusRef={filterToggle}
					id={documentToDelete.id}
					onClose={() => setDocumentToDelete(undefined)}
					onDelete={async () => {
						await deleteDocument.mutateAsync({
							params: {
								path: {
									table_id: tableId,
									doc_id: documentToDelete.id,
								},
							},
						});
						if (selectedDocument?.id === documentToDelete.id)
							closeInspector();
					}}
				/>
			)}
		</PageWorkspace>
	);
}
