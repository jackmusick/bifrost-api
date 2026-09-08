import { useState, useMemo, useRef } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { ArrowLeft, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	PageScrollArea,
	PageWorkspace,
} from "@/components/layout/PageWorkspace";
import { useTable, useDocuments, useDeleteDocument } from "@/services/tables";
import { DocumentDialog } from "@/components/tables/DocumentDialog";
import { TableFilterSidebar } from "@/components/tables/TableFilterSidebar";
import { DocumentRecordList } from "@/components/tables/DocumentRecordList";
import { SearchBox } from "@/components/search/SearchBox";
import { useSearch } from "@/hooks/useSearch";
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
	const documentsQuery = useDocuments(tableId, query);
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
			).slice(0, 3),
		[documents],
	);
	const handleAdd = () => {
		setSelectedDocument(undefined);
		setIsDialogOpen(true);
	};
	const handleEdit = (doc: DocumentPublic) => {
		setSelectedDocument(doc);
		setIsDialogOpen(true);
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
		<PageWorkspace>
			<TableDetailHeader
				name={table.name}
				description={table.description}
				backTo={backTo}
				backLabel={backLabel}
				refreshing={documentsQuery.isFetching}
				onRefresh={() => void documentsQuery.refetch()}
				onAdd={handleAdd}
			/>
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
			<div className="flex flex-col gap-3 sm:flex-row sm:items-start">
				<div className="min-w-0 flex-1">
					<SearchBox
						value={searchTerm}
						onChange={setSearchTerm}
						placeholder="Search this page…"
						aria-label="Search documents on this page"
						className="w-full"
					/>
					<p className="mt-2 text-xs text-muted-foreground">
						Search checks this page. Use filters to query the entire
						table.
					</p>
				</div>
				<Button
					ref={filterToggle}
					type="button"
					variant="outline"
					className="min-h-11"
					aria-expanded={sidebarOpen}
					aria-controls="document-filters"
					onClick={() => setSidebarOpen((open) => !open)}
				>
					<SlidersHorizontal aria-hidden="true" className="size-4" />
					Filters
					{hasActiveFilters
						? ` (${Object.keys(whereClause).length})`
						: ""}
				</Button>
			</div>
			<PageScrollArea className="lg:flex lg:flex-col lg:overflow-hidden">
				<div className="flex min-w-0 flex-col gap-6 lg:flex-row lg:h-full lg:min-h-0">
					<div
						id="document-filters"
						hidden={!sidebarOpen}
						className="w-full shrink-0 lg:max-h-full lg:w-64 lg:overflow-auto xl:w-72"
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
							className="w-full"
						/>
					</div>
					<section
						aria-label="Documents"
						className="min-w-0 w-full flex-1 space-y-4 lg:flex lg:min-h-0 lg:flex-col lg:gap-4 lg:space-y-0"
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
								busy={documentsQuery.isFetching}
								action="Retry documents"
								onAction={() => void documentsQuery.refetch()}
							/>
						)}
						{documentsQuery.isLoading ? (
							<DocumentCollectionState title="Loading documents…" />
						) : (
							<>
								{documentsQuery.isFetching && (
									<p
										role="status"
										className="text-sm text-muted-foreground"
									>
										Refreshing documents…
									</p>
								)}
								{filteredDocuments.length > 0 ? (
									<DocumentRecordList
										documents={filteredDocuments}
										dataColumns={dataColumns}
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
										busy={documentsQuery.isFetching}
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
				</div>
			</PageScrollArea>
			<DocumentDialog
				returnFocusRef={filterToggle}
				document={selectedDocument}
				tableId={tableId}
				open={isDialogOpen}
				onClose={() => {
					setIsDialogOpen(false);
					setSelectedDocument(undefined);
				}}
			/>
			{documentToDelete && (
				<DocumentDeleteDialog
					key={documentToDelete.id}
					returnFocusRef={filterToggle}
					id={documentToDelete.id}
					onClose={() => setDocumentToDelete(undefined)}
					onDelete={() =>
						deleteDocument.mutateAsync({
							params: {
								path: {
									table_id: tableId,
									doc_id: documentToDelete.id,
								},
							},
						})
					}
				/>
			)}
		</PageWorkspace>
	);
}
