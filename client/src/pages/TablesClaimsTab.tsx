import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
	Building2,
	KeyRound,
	Pencil,
	Plus,
	RefreshCw,
	Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { CustomClaimEditor } from "@/components/tables/CustomClaimEditor";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { ClaimDeleteDialog } from "./tables/ClaimDeleteDialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { SearchBox } from "@/components/search/SearchBox";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { useAuth } from "@/contexts/AuthContext";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { ListToolbar } from "@/components/layout/ListToolbar";
import { useSearch } from "@/hooks/useSearch";
import {
	createClaim,
	deleteClaim,
	listClaims,
	updateClaim,
	type CustomClaim,
} from "@/services/claims";

interface EditingState {
	claim: CustomClaim;
	originalName: string | null;
	scope?: string;
}

const EMPTY_CLAIM: CustomClaim = {
	id: "00000000-0000-4000-8000-000000000000",
	organization_id: "00000000-0000-4000-8000-000000000000",
	name: "",
	description: "",
	type: "list",
	query: { table: "", select: "" },
	is_solution_managed: false,
};

export function TablesClaimsTab() {
	const addClaimRef = useRef<HTMLButtonElement>(null);
	const compactLayout = useMediaQuery("(max-width: 1023px)");
	const { isPlatformAdmin, user } = useAuth();
	const { data: organizations } = useOrganizations({
		enabled: isPlatformAdmin,
	});

	const [searchTerm, setSearchTerm] = useState("");
	const [filterOrgId, setFilterOrgId] = useState<string | null | undefined>(
		undefined,
	);
	const [editing, setEditing] = useState<EditingState | null>(null);
	const [claimToDelete, setClaimToDelete] = useState<CustomClaim | null>(
		null,
	);

	const orgNameById = useMemo(() => {
		const m = new Map<string, string>();
		for (const o of organizations ?? []) m.set(o.id, o.name);
		return m;
	}, [organizations]);

	const getOrgName = (orgId?: string | null): string =>
		orgId ? (orgNameById.get(orgId) ?? orgId) : "Global";

	const getClaimScope = (claim: CustomClaim): string | undefined =>
		claim.organization_id ?? undefined;

	const apiScope =
		filterOrgId === undefined || filterOrgId === null
			? undefined
			: filterOrgId;

	const {
		data,
		error,
		isFetching: loading,
		isLoading: initialLoading,
		refetch: refresh,
	} = useQuery({
		queryKey: ["custom-claims", { scope: apiScope }],
		queryFn: ({ signal }) => listClaims({ signal, scope: apiScope }),
	});
	const claims = data?.claims ?? [];
	const hasLoaded = data !== undefined;
	const loadError = Boolean(error);

	const filteredClaims = useSearch(claims, searchTerm, [
		"name",
		"description",
	]);

	async function handleSave(claim: CustomClaim) {
		if (editing?.originalName) {
			await updateClaim(
				editing.originalName,
				{
					description: claim.description,
					type: claim.type,
					query: claim.query,
				},
				{ scope: editing.scope },
			);
			toast.success("Claim updated");
		} else {
			await createClaim(
				{
					name: claim.name,
					description: claim.description,
					type: claim.type,
					query: claim.query,
				},
				{ scope: editing?.scope },
			);
			toast.success("Claim created");
		}
		setEditing(null);
		await refresh();
	}

	async function handleDeleteConfirmed() {
		if (!claimToDelete) return;
		await deleteClaim(claimToDelete.name, {
			scope: getClaimScope(claimToDelete),
		});
		toast.success("Claim deleted");
		setClaimToDelete(null);
		await refresh();
	}

	function handleAdd() {
		const defaultOrg = user?.organizationId ?? "";
		setEditing({
			claim: { ...EMPTY_CLAIM, organization_id: defaultOrg },
			originalName: null,
			scope: defaultOrg,
		});
	}

	const renderClaimActions = (claim: CustomClaim) => (
		<RecordActionsMenu label={`${claim.name} actions`}>
			<DropdownMenuItem
				className="min-h-11"
				onSelect={() =>
					setEditing({
						claim,
						originalName: claim.name,
						scope: getClaimScope(claim),
					})
				}
			>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11"
				onSelect={() => setClaimToDelete(claim)}
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);

	if (editing) {
		return (
			<div className="py-4">
				<CustomClaimEditor
					value={editing.claim}
					onChange={(claim) => setEditing({ ...editing, claim })}
					onSave={handleSave}
					onCancel={() => setEditing(null)}
					nameDisabled={editing.originalName !== null}
				/>
			</div>
		);
	}

	return (
		<div className="flex flex-1 min-h-0 flex-col space-y-6">
			<ListToolbar>
				<SearchBox
					value={searchTerm}
					onChange={setSearchTerm}
					aria-label="Search custom claims"
					placeholder="Search custom claims by name or description..."
					className="w-full sm:flex-1"
				/>
				{isPlatformAdmin && (
					<div className="w-full sm:w-64">
						<OrganizationSelect
							value={filterOrgId}
							onChange={setFilterOrgId}
							showAll={true}
							showGlobal={false}
							placeholder="All organizations"
						/>
					</div>
				)}
				<div className="flex items-center gap-2 sm:ml-auto">
					<Button
						variant="outline"
						size="icon"
						onClick={() => refresh()}
						title="Refresh"
						aria-label="Refresh claims"
						disabled={loading}
						className="h-11 w-11 lg:h-10 lg:w-10"
					>
						<RefreshCw
							className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`}
						/>
					</Button>
					<Button
						className="min-h-11 flex-1 sm:flex-none lg:min-h-10"
						onClick={handleAdd}
						ref={addClaimRef}
						title="Add Claim"
						aria-label="Add Claim"
					>
						<Plus className="h-4 w-4" />
						New claim
					</Button>
				</div>
			</ListToolbar>

			{loadError && (
				<Alert variant="destructive">
					<AlertTitle>Custom claims could not be loaded</AlertTitle>
					<AlertDescription className="space-y-3">
						<p>
							{hasLoaded
								? "Showing the last loaded claims. Refresh to get the latest changes."
								: "Try again to load your claims. Your search is preserved."}
						</p>
						<Button
							variant="outline"
							className="min-h-11"
							disabled={loading}
							onClick={() => refresh()}
						>
							Retry claims
						</Button>
					</AlertDescription>
				</Alert>
			)}
			{initialLoading ? (
				<div
					role="status"
					aria-label="Loading custom claims"
					className="space-y-2"
				>
					<span className="sr-only">Loading custom claims…</span>
					{[...Array(5)].map((_, i) => (
						<Skeleton key={i} className="h-12 w-full" />
					))}
				</div>
			) : loadError && !hasLoaded ? null : filteredClaims.length > 0 ? (
				<div className="flex-1 min-h-0">
					{compactLayout ? (
						<ul
							aria-label="Custom claims"
							className="divide-y rounded-[var(--bf-radius-surface)] border bg-card"
						>
							{filteredClaims.map((claim) => (
								<li key={claim.id} className="space-y-3 p-4">
									<h2 className="font-mono text-sm font-semibold [overflow-wrap:anywhere]">
										{claim.name}
									</h2>
									<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
										{claim.description || "No description"}
									</p>
									<dl className="grid gap-3 text-sm">
										{isPlatformAdmin && (
											<div>
												<dt className="text-xs text-muted-foreground">
													Organization
												</dt>
												<dd className="mt-1 [overflow-wrap:anywhere]">
													{getOrgName(
														claim.organization_id,
													)}
												</dd>
											</div>
										)}
										<div>
											<dt className="text-xs text-muted-foreground">
												Type
											</dt>
											<dd className="mt-1">
												{claim.type}
											</dd>
										</div>
										<div>
											<dt className="text-xs text-muted-foreground">
												Source table
											</dt>
											<dd className="mt-1 font-mono text-xs [overflow-wrap:anywhere]">
												{claim.query.table}
											</dd>
										</div>
										<div>
											<dt className="text-xs text-muted-foreground">
												Select
											</dt>
											<dd className="mt-1 font-mono text-xs [overflow-wrap:anywhere]">
												{claim.query.select}
											</dd>
										</div>
									</dl>
									{claim.is_solution_managed ? (
										<div className="flex flex-wrap items-center gap-2 border-t pt-3">
											<SolutionManagedBadge
												solutionId={claim.solution_id}
											/>
											<span className="text-xs text-muted-foreground">
												Edits are managed through
												deployment.
											</span>
										</div>
									) : (
										<div className="border-t pt-3">
											{renderClaimActions(claim)}
										</div>
									)}
								</li>
							))}
						</ul>
					) : (
						<DataTable className="max-h-full">
							<DataTableHeader>
								<DataTableRow>
									{isPlatformAdmin && (
										<DataTableHead className="w-0 whitespace-nowrap">
											Organization
										</DataTableHead>
									)}
									<DataTableHead>Name</DataTableHead>
									<DataTableHead>Description</DataTableHead>
									<DataTableHead className="w-0 whitespace-nowrap">
										Type
									</DataTableHead>
									<DataTableHead className="w-0 whitespace-nowrap">
										Source table
									</DataTableHead>
									<DataTableHead className="w-0 whitespace-nowrap">
										Select
									</DataTableHead>
									<DataTableHead className="w-0 whitespace-nowrap text-right" />
								</DataTableRow>
							</DataTableHeader>
							<DataTableBody>
								{filteredClaims.map((claim) => (
									<DataTableRow
										key={claim.id}
										className={
											claim.is_solution_managed
												? "hover:bg-muted/50"
												: "cursor-pointer hover:bg-muted/50"
										}
										onClick={() => {
											if (claim.is_solution_managed)
												return;
											setEditing({
												claim,
												originalName: claim.name,
												scope: getClaimScope(claim),
											});
										}}
									>
										{isPlatformAdmin && (
											<DataTableCell className="w-0 whitespace-nowrap">
												<Badge
													variant="outline"
													className="gap-1"
												>
													<Building2 className="h-3 w-3" />
													{getOrgName(
														claim.organization_id,
													)}
												</Badge>
											</DataTableCell>
										)}
										<DataTableCell className="font-mono font-medium">
											<div className="flex items-center gap-2">
												{claim.name}
												<SolutionManagedBadge
													solutionId={
														claim.solution_id
													}
												/>
											</div>
										</DataTableCell>
										<DataTableCell className="max-w-xs truncate text-muted-foreground">
											{claim.description || "-"}
										</DataTableCell>
										<DataTableCell className="w-0 whitespace-nowrap text-sm text-muted-foreground">
											{claim.type}
										</DataTableCell>
										<DataTableCell className="w-0 whitespace-nowrap font-mono text-sm">
											{claim.query.table}
										</DataTableCell>
										<DataTableCell className="w-0 whitespace-nowrap font-mono text-sm">
											{claim.query.select}
										</DataTableCell>
										<DataTableCell
											className="w-0 whitespace-nowrap text-right"
											onClick={(e) => e.stopPropagation()}
										>
											{!claim.is_solution_managed &&
												renderClaimActions(claim)}
										</DataTableCell>
									</DataTableRow>
								))}
							</DataTableBody>
						</DataTable>
					)}
				</div>
			) : (
				<Card>
					<CardContent className="flex flex-col items-center justify-center py-12 text-center">
						<KeyRound className="h-12 w-12 text-muted-foreground" />
						<h3 className="mt-4 text-lg font-semibold">
							{searchTerm
								? "No custom claims match your search"
								: "No custom claims yet"}
						</h3>
						<p className="mt-2 text-sm text-muted-foreground">
							{searchTerm
								? "Try adjusting your search term or clear the filter"
								: "Custom claims are reusable query-resolved facts you can reference from table policies."}
						</p>
						{!searchTerm && (
							<Button
								variant="outline"
								onClick={handleAdd}
								className="mt-4"
							>
								<Plus className="mr-2 h-4 w-4" />
								Create your first custom claim
							</Button>
						)}
					</CardContent>
				</Card>
			)}

			{claimToDelete && (
				<ClaimDeleteDialog
					name={claimToDelete.name}
					onConfirm={handleDeleteConfirmed}
					onOpenChange={(open) => !open && setClaimToDelete(null)}
					returnFocusRef={addClaimRef}
				/>
			)}
		</div>
	);
}
