import { TableActionsMenu } from "./tables/TableActionsMenu";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
	Database,
	Plus,
	RefreshCw,
	Globe,
	Building2,
	Download,
	Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { TableDeleteDialog } from "./tables/TableDeleteDialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SearchBox } from "@/components/search/SearchBox";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { ListToolbar } from "@/components/layout/ListToolbar";
import { PageWorkspace } from "@/components/layout/PageWorkspace";
import { TableRecordList } from "@/components/tables/TableRecordList";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";
import { useAuth } from "@/contexts/AuthContext";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useTables, useDeleteTable } from "@/services/tables";
import { TableDialog } from "@/components/tables/TableDialog";
import { TablesClaimsTab } from "@/pages/TablesClaimsTab";
import { ImportDialog } from "@/components/ImportDialog";
import { exportEntities } from "@/services/exportImport";
import { toast } from "sonner";
import type { TablePublic } from "@/services/tables";

export function Tables() {
	const createButtonRef = useRef<HTMLButtonElement>(null);
	const compactLayout = useMediaQuery("(max-width: 1023px)");
	const navigate = useNavigate();
	const [activeTab, setActiveTab] = useState("tables");
	const { isPlatformAdmin } = useAuth();
	const [selectedTable, setSelectedTable] = useState<
		TablePublic | undefined
	>();
	const [isDialogOpen, setIsDialogOpen] = useState(false);
	const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
	const [tableToDelete, setTableToDelete] = useState<
		TablePublic | undefined
	>();
	const [searchTerm, setSearchTerm] = useState("");
	const [filterOrgId, setFilterOrgId] = useState<string | null | undefined>(
		undefined,
	);
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [isImportOpen, setIsImportOpen] = useState(false);
	const [isExporting, setIsExporting] = useState(false);

	// Convert filterOrgId to scope for API: undefined = all, null = global only, string = org UUID
	const apiScope =
		filterOrgId === undefined
			? undefined
			: filterOrgId === null
				? "global"
				: filterOrgId;

	const { data, isLoading, isFetching, error, refetch } = useTables(apiScope);
	const deleteTable = useDeleteTable();

	// Fetch organizations for the org name lookup (platform admins only)
	const { data: organizations } = useOrganizations({
		enabled: isPlatformAdmin,
	});

	// Helper to get organization name from ID
	const getOrgName = (orgId: string | null | undefined): string => {
		if (!orgId) return "Global";
		const org = organizations?.find((o) => o.id === orgId);
		return org?.name || orgId;
	};

	const tables = data?.tables ?? [];

	// Apply search filter
	const filteredTables = useSearch(tables, searchTerm, [
		"name",
		"description",
	]);

	const handleEdit = (table: TablePublic) => {
		setSelectedTable(table);
		setIsDialogOpen(true);
	};

	const handleAdd = () => {
		setSelectedTable(undefined);
		setIsDialogOpen(true);
	};

	const handleDelete = (table: TablePublic) => {
		setTableToDelete(table);
		setIsDeleteDialogOpen(true);
	};

	const handleConfirmDelete = async () => {
		if (!tableToDelete) return;
		// Defense in depth: solution-managed tables are deploy-owned and
		// read-only on the platform (server returns 409). The Delete button is
		// already disabled for them; this guards the bulk/stale-render path so we
		// never round-trip to a raw 409 (audit U1).
		if (tableToDelete.is_solution_managed) {
			toast.error(
				"Solution-managed entities can only be managed by deployment methods.",
			);
			setIsDeleteDialogOpen(false);
			setTableToDelete(undefined);
			return;
		}
		await deleteTable.mutateAsync({
			params: {
				path: { table_id: tableToDelete.id },
			},
		});
		setIsDeleteDialogOpen(false);
		setTableToDelete(undefined);
	};

	const handleViewDocuments = (table: TablePublic) => {
		navigate(`/tables/${table.id}`);
	};

	const handleDialogClose = () => {
		setIsDialogOpen(false);
		setSelectedTable(undefined);
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
		filteredTables.length > 0 &&
		filteredTables.every((table) => selectedIds.has(table.id));
	const someVisibleSelected = filteredTables.some((table) =>
		selectedIds.has(table.id),
	);
	const toggleSelectAll = () => {
		setSelectedIds((previous) => {
			const next = new Set(previous);
			for (const table of filteredTables) {
				if (allVisibleSelected) next.delete(table.id);
				else next.add(table.id);
			}
			return next;
		});
	};

	const handleExport = async () => {
		const ids = selectedIds.size > 0 ? Array.from(selectedIds) : [];
		setIsExporting(true);
		try {
			await exportEntities("tables", ids);
			toast.success("Export downloaded");
		} catch {
			toast.error("Export failed");
		} finally {
			setIsExporting(false);
		}
	};

	const formatDate = (dateStr: string | null) => {
		if (!dateStr) return "-";
		return new Date(dateStr).toLocaleDateString(undefined, {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	};

	const renderTableActions = (table: TablePublic) => (
		<TableActionsMenu
			table={table}
			onEdit={() => handleEdit(table)}
			onDelete={() => handleDelete(table)}
		/>
	);

	return (
		<PageWorkspace className="max-w-7xl mx-auto">
			<ListPageHeader
				title="Data Tables"
				description="Manage document tables for your applications"
				actions={
					activeTab === "tables" ? (
						<>
							<Button
								variant="outline"
								size="icon"
								onClick={() => refetch()}
								title="Refresh"
								aria-label="Refresh"
								disabled={isFetching}
								className="h-11 w-11 lg:h-10 lg:w-10"
							>
								<RefreshCw
									className={`h-4 w-4 ${isFetching ? "animate-spin motion-reduce:animate-none" : ""}`}
								/>
							</Button>
							<Button
								variant="default"
								ref={createButtonRef}
								onClick={handleAdd}
								title="Create table"
								aria-label="Create table"
								className="min-h-11 min-w-0 lg:min-h-10"
							>
								<Plus className="h-4 w-4" />
								New table
							</Button>
						</>
					) : undefined
				}
			/>

			<Tabs
				value={activeTab}
				onValueChange={setActiveTab}
				className="flex flex-1 min-h-0 flex-col"
			>
				<TabsList className="w-fit">
					<TabsTrigger value="tables">Tables</TabsTrigger>
					<TabsTrigger value="claims">Custom Claims</TabsTrigger>
				</TabsList>

				<TabsContent
					value="tables"
					className="flex flex-1 min-h-0 flex-col space-y-6"
				>
					<ListToolbar>
						<SearchBox
							value={searchTerm}
							onChange={setSearchTerm}
							aria-label="Search tables"
							placeholder="Search tables by name or description..."
							className="w-full sm:flex-1"
						/>
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
						{isPlatformAdmin && (
							<div className="flex flex-wrap items-center gap-2 sm:ml-auto">
								{selectedIds.size > 0 && (
									<span className="text-sm text-muted-foreground">
										{selectedIds.size} selected
									</span>
								)}
								<Button
									variant="outline"
									size="sm"
									className="min-h-11 lg:min-h-9"
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
									size="sm"
									className="min-h-11 lg:min-h-9"
									onClick={() => setIsImportOpen(true)}
								>
									<Upload className="h-4 w-4 mr-1" />
									Import
								</Button>
							</div>
						)}
					</ListToolbar>

					{error && (
						<Alert variant="destructive">
							<AlertTitle>Tables could not be loaded</AlertTitle>
							<AlertDescription className="space-y-3">
								<p>
									{data
										? "Showing the last loaded tables. Refresh to get the latest changes."
										: "Try again to load your tables. Your filters are preserved."}
								</p>
								<Button
									variant="outline"
									className="min-h-11"
									disabled={isFetching}
									onClick={() => refetch()}
								>
									{isFetching ? "Retrying…" : "Retry tables"}
								</Button>
							</AlertDescription>
						</Alert>
					)}
					{/* Content */}
					{isLoading ? (
						<div
							role="status"
							aria-label="Loading tables"
							className="space-y-2"
						>
							<span className="sr-only">Loading tables…</span>
							{[...Array(5)].map((_, i) => (
								<Skeleton key={i} className="h-12 w-full" />
							))}
						</div>
					) : error && !data ? null : filteredTables &&
					  filteredTables.length > 0 ? (
						<div
							className="flex-1 min-h-0"
							role="region"
							aria-label="Data tables"
						>
							{compactLayout ? (
								<TableRecordList
									tables={filteredTables}
									isPlatformAdmin={isPlatformAdmin}
									selectedIds={selectedIds}
									allVisibleSelected={allVisibleSelected}
									someVisibleSelected={someVisibleSelected}
									onToggleAll={toggleSelectAll}
									onToggle={toggleSelect}
									scopeName={getOrgName}
									formatDate={formatDate}
									renderActions={renderTableActions}
								/>
							) : (
								<DataTable className="max-h-full">
									<DataTableHeader>
										<DataTableRow>
											{isPlatformAdmin && (
												<DataTableHead className="w-10">
													<Checkbox
														aria-label="Select visible tables"
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
											<DataTableHead>Name</DataTableHead>
											<DataTableHead>
												Description
											</DataTableHead>
											<DataTableHead className="w-0 whitespace-nowrap">
												Created
											</DataTableHead>
											<DataTableHead className="w-0 whitespace-nowrap text-right" />
										</DataTableRow>
									</DataTableHeader>
									<DataTableBody>
										{filteredTables.map((table) => (
											<DataTableRow
												key={table.id}
												clickable
												href={`/tables/${table.id}`}
												onClick={() =>
													handleViewDocuments(table)
												}
											>
												{isPlatformAdmin && (
													<DataTableCell>
														<Checkbox
															aria-label={`Select ${table.name}`}
															checked={selectedIds.has(
																table.id,
															)}
															onCheckedChange={() =>
																toggleSelect(
																	table.id,
																)
															}
															onClick={(
																e: React.MouseEvent,
															) =>
																e.stopPropagation()
															}
														/>
													</DataTableCell>
												)}
												<DataTableCell className="w-0 whitespace-nowrap">
													{table.organization_id ? (
														<Badge
															variant="outline"
															className="gap-1"
														>
															<Building2 className="h-3 w-3" />
															{isPlatformAdmin
																? getOrgName(
																		table.organization_id,
																	)
																: "Organization"}
														</Badge>
													) : (
														<Badge
															variant="secondary"
															className="gap-1"
														>
															<Globe className="h-3 w-3" />
															Global
														</Badge>
													)}
												</DataTableCell>
												<DataTableCell className="min-w-0 font-medium font-mono">
													<span className="flex min-w-0 items-center gap-2">
														<span className="truncate">
															{table.name}
														</span>
														{table.is_solution_managed && (
															<SolutionManagedBadge
																solutionId={
																	table.solution_id
																}
															/>
														)}
													</span>
												</DataTableCell>
												<DataTableCell className="max-w-xs truncate text-muted-foreground">
													{table.description || "-"}
												</DataTableCell>
												<DataTableCell className="w-0 whitespace-nowrap text-sm text-muted-foreground">
													{formatDate(
														table.created_at,
													)}
												</DataTableCell>
												<DataTableCell className="w-0 whitespace-nowrap text-right">
													{renderTableActions(table)}
												</DataTableCell>
											</DataTableRow>
										))}
									</DataTableBody>
								</DataTable>
							)}
						</div>
					) : (
						// Empty State
						<Card>
							<CardContent className="flex flex-col items-center justify-center py-12 text-center">
								<Database className="h-12 w-12 text-muted-foreground" />
								<h3 className="mt-4 text-lg font-semibold">
									{searchTerm
										? "No tables match your search"
										: "No tables found"}
								</h3>
								<p className="mt-2 text-sm text-muted-foreground">
									{searchTerm
										? "Try adjusting your search term or clear the filter"
										: "Get started by creating your first data table"}
								</p>
								{!searchTerm && (
									<Button
										variant="outline"
										onClick={handleAdd}
										className="mt-4"
									>
										<Plus className="mr-2 h-4 w-4" />
										Create your first table
									</Button>
								)}
							</CardContent>
						</Card>
					)}
				</TabsContent>

				<TabsContent value="claims" className="flex-1 min-h-0">
					<TablesClaimsTab />
				</TabsContent>
			</Tabs>

			<TableDialog
				table={selectedTable}
				open={isDialogOpen}
				onClose={handleDialogClose}
			/>

			<ImportDialog
				open={isImportOpen}
				onOpenChange={setIsImportOpen}
				entityType="tables"
				onImportComplete={() => refetch()}
			/>

			{isDeleteDialogOpen && tableToDelete && (
				<TableDeleteDialog
					name={tableToDelete.name}
					onConfirm={handleConfirmDelete}
					onOpenChange={setIsDeleteDialogOpen}
					returnFocusRef={createButtonRef}
				/>
			)}
		</PageWorkspace>
	);
}
