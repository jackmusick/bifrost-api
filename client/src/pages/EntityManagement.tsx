import { EntityAssignmentSheet } from "@/components/entity-management/EntityAssignmentSheet";
import { isEntityManaged } from "@/components/entity-management/types";
import { deleteEntities } from "@/components/entity-management/deleteEntities";
import { EntityCollectionStatus } from "@/components/entity-management/EntityCollectionStatus";
import { EntityListToolbar } from "@/components/entity-management/EntityListToolbar";
import { useAssignEntityRole } from "@/hooks/useAssignEntityRole";
import { EntityAssignmentPanel } from "@/components/entity-management/EntityAssignmentPanel";
import { useState, useMemo, useCallback, useRef } from "react";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { RefreshCw, Filter } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkflows, useUpdateWorkflow } from "@/hooks/useWorkflows";
import { useForms, useUpdateForm } from "@/hooks/useForms";
import { useAgents, useUpdateAgent } from "@/hooks/useAgents";
import { useApplications, useUpdateApplication } from "@/hooks/useApplications";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useRoles } from "@/hooks/useRoles";
import {
	useDependencyGraph,
	type EntityType as DependencyEntityType,
} from "@/hooks/useDependencyGraph";
import { WorkflowDeactivationDialog } from "@/components/editor/WorkflowDeactivationDialog";
import { authFetch } from "@/lib/api-client";
import { toast } from "sonner";
import type { components } from "@/lib/v1";

import {
	EntityCard,
	FilterPopover,
	DependencyGraphDialog,
	RelationshipFilterBanner,
	DeleteConfirmDialog,
	normalizeEntities,
	type EntityType,
	type RelationshipFilter,
	type SortOption,
	type ApplicationPublic,
} from "@/components/entity-management";

export function EntityManagement() {
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [searchTerm, setSearchTerm] = useState("");
	const [typeFilter, setTypeFilter] = useState<string>("all");
	const [orgFilter, setOrgFilter] = useState<string>("all");
	const [accessFilter, setAccessFilter] = useState<string>("all");
	const [usageFilter, setUsageFilter] = useState<string>("all");
	const [sortBy, setSortBy] = useState<SortOption>("name");
	const [sortAsc, setSortAsc] = useState(true);
	const [isUpdating, setIsUpdating] = useState(false);
	const [updatingMessage, setUpdatingMessage] = useState("Updating...");

	// Relationship filter state
	const [relationshipFilter, setRelationshipFilter] =
		useState<RelationshipFilter | null>(null);
	const [isGraphDialogOpen, setIsGraphDialogOpen] = useState(false);

	// Confirm delete state (for non-workflow entities: forms, agents, apps)
	const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
	const [confirmDeleteEntities, setConfirmDeleteEntities] = useState<
		{ id: string; name: string; entityType: EntityType; slug?: string }[]
	>([]);
	const [isDeleting, setIsDeleting] = useState(false);
	const deleteBusy = useRef(false);
	const [deleteFailures, setDeleteFailures] = useState<
		{ entity: { id: string; name: string }; message: string }[]
	>([]);

	// Workflow delete state
	const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
	const [deletingWorkflowId, setDeletingWorkflowId] = useState<string | null>(
		null,
	);
	const [pendingDeactivations, setPendingDeactivations] = useState<
		components["schemas"]["PendingDeactivation"][]
	>([]);
	const [availableReplacements, setAvailableReplacements] = useState<
		components["schemas"]["AvailableReplacement"][]
	>([]);
	// Track workflow IDs that returned 409 during bulk delete (for Phase 2)
	const [conflictWorkflowIds, setConflictWorkflowIds] = useState<string[]>(
		[],
	);

	// Fetch all entity types
	const {
		data: workflows,
		isLoading: loadingWorkflows,
		isError: errorWorkflows,
		isFetching: fetchingWorkflows,
		refetch: refetchWorkflows,
	} = useWorkflows();
	const {
		data: forms,
		isLoading: loadingForms,
		isError: errorForms,
		isFetching: fetchingForms,
		refetch: refetchForms,
	} = useForms();
	const {
		data: agents,
		isLoading: loadingAgents,
		isError: errorAgents,
		isFetching: fetchingAgents,
		refetch: refetchAgents,
	} = useAgents();
	const {
		data: appsResponse,
		isLoading: loadingApps,
		isError: errorApps,
		isFetching: fetchingApps,
		refetch: refetchApps,
	} = useApplications();
	const {
		data: organizations,
		isLoading: loadingOrganizations,
		isError: errorOrganizations,
		isFetching: fetchingOrganizations,
		refetch: refetchOrganizations,
	} = useOrganizations();
	const {
		data: roles,
		isLoading: loadingRoles,
		isError: errorRoles,
		isFetching: fetchingRoles,
		refetch: refetchRoles,
	} = useRoles();

	// Fetch dependency graph when relationship filter is active
	const {
		data: graphData,
		isLoading: loadingGraph,
		isError: graphError,
		isFetching: fetchingGraph,
		refetch: refetchGraph,
	} = useDependencyGraph(
		relationshipFilter
			? (relationshipFilter.entityType as DependencyEntityType)
			: undefined,
		relationshipFilter?.entityId,
		3, // Fixed depth of 3 for relationship filtering
	);

	// Update mutations
	const assignEntityRole = useAssignEntityRole();
	const updateWorkflow = useUpdateWorkflow();
	const updateForm = useUpdateForm();
	const updateAgent = useUpdateAgent();
	const updateApplication = useUpdateApplication();

	const isLoading =
		loadingWorkflows || loadingForms || loadingAgents || loadingApps;

	const collections = [
		{
			name: "Workflows",
			isLoading: loadingWorkflows,
			isError: errorWorkflows,
			isFetching: fetchingWorkflows,
			hasData: workflows !== undefined,
			onRetry: () => void refetchWorkflows(),
		},
		{
			name: "Forms",
			isLoading: loadingForms,
			isError: errorForms,
			isFetching: fetchingForms,
			hasData: forms !== undefined,
			onRetry: () => void refetchForms(),
		},
		{
			name: "Agents",
			isLoading: loadingAgents,
			isError: errorAgents,
			isFetching: fetchingAgents,
			hasData: agents !== undefined,
			onRetry: () => void refetchAgents(),
		},
		{
			name: "Apps",
			isLoading: loadingApps,
			isError: errorApps,
			isFetching: fetchingApps,
			hasData: appsResponse !== undefined,
			onRetry: () => void refetchApps(),
		},
		{
			name: "Organizations",
			isLoading: loadingOrganizations,
			isError: errorOrganizations,
			isFetching: fetchingOrganizations,
			hasData: organizations !== undefined,
			onRetry: () => void refetchOrganizations(),
		},
		{
			name: "Roles",
			isLoading: loadingRoles,
			isError: errorRoles,
			isFetching: fetchingRoles,
			hasData: roles !== undefined,
			onRetry: () => void refetchRoles(),
		},
	];
	const incompleteEntityData =
		errorWorkflows || errorForms || errorAgents || errorApps;

	// Normalize and combine all entities
	const allEntities = useMemo(
		() =>
			normalizeEntities(
				workflows ?? [],
				forms ?? [],
				agents ?? [],
				appsResponse?.applications ?? [],
			),
		[workflows, forms, agents, appsResponse],
	);

	// Extract related entity IDs from graph data
	const relatedEntityIds = useMemo(() => {
		if (!relationshipFilter || !graphData?.nodes) return null;

		const ids = new Set<string>();
		for (const node of graphData.nodes) {
			const parts = node.id.split(":");
			if (parts.length === 2) {
				ids.add(parts[1]);
			} else {
				ids.add(node.id);
			}
		}
		return ids;
	}, [relationshipFilter, graphData]);

	// Apply filters
	const filteredEntities = useMemo(() => {
		let result = allEntities;

		if (relationshipFilter) {
			// Relationship mode: only filter by related IDs + search
			result = relatedEntityIds
				? result.filter((e) => relatedEntityIds.has(e.id))
				: [];
		} else {
			// Normal mode: apply all standard filters
			if (typeFilter !== "all") {
				result = result.filter((e) => e.entityType === typeFilter);
			}

			if (orgFilter !== "all") {
				if (orgFilter === "global") {
					result = result.filter((e) => !e.organizationId);
				} else {
					result = result.filter(
						(e) => e.organizationId === orgFilter,
					);
				}
			}

			if (accessFilter !== "all") {
				result = result.filter((e) => e.accessLevel === accessFilter);
			}

			if (usageFilter !== "all") {
				if (usageFilter === "unused") {
					result = result.filter((e) => e.usedByCount === 0);
				} else if (usageFilter === "in_use") {
					result = result.filter(
						(e) => e.usedByCount !== null && e.usedByCount > 0,
					);
				}
			}
		}

		if (searchTerm) {
			const term = searchTerm.toLowerCase();
			result = result.filter((e) => e.name.toLowerCase().includes(term));
		}

		result = [...result].sort((a, b) => {
			let cmp = 0;
			switch (sortBy) {
				case "name":
					cmp = a.name.localeCompare(b.name);
					break;
				case "date":
					cmp = a.createdAt.localeCompare(b.createdAt);
					break;
				case "type":
					cmp = a.entityType.localeCompare(b.entityType);
					break;
			}
			return sortAsc ? cmp : -cmp;
		});

		return result;
	}, [
		allEntities,
		relationshipFilter,
		relatedEntityIds,
		typeFilter,
		orgFilter,
		accessFilter,
		usageFilter,
		searchTerm,
		sortBy,
		sortAsc,
	]);

	const activeFilterCount =
		(typeFilter !== "all" ? 1 : 0) +
		(orgFilter !== "all" ? 1 : 0) +
		(accessFilter !== "all" ? 1 : 0) +
		(usageFilter !== "all" ? 1 : 0);

	const handleClearFilters = () => {
		setTypeFilter("all");
		setOrgFilter("all");
		setAccessFilter("all");
		setUsageFilter("all");
	};

	const handleRefresh = () => {
		void refetchOrganizations();
		void refetchRoles();
		if (relationshipFilter) void refetchGraph();
		refetchWorkflows();
		refetchForms();
		refetchAgents();
		refetchApps();
	};

	const handleSelectEntity = (entityId: string, selected: boolean) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (selected) {
				next.add(entityId);
			} else {
				next.delete(entityId);
			}
			return next;
		});
	};

	const handleSelectAll = (selected: boolean) => {
		if (selected) {
			setSelectedIds(
				new Set(
					filteredEntities
						.filter((e) => !isEntityManaged(e))
						.map((e) => e.id),
				),
			);
		} else {
			setSelectedIds(new Set());
		}
	};

	const handleShowRelationships = useCallback(
		(entityId: string, entityType: EntityType, entityName: string) => {
			setRelationshipFilter({
				entityId,
				entityType,
				entityName,
			});
		},
		[],
	);

	const handleClearRelationshipFilter = useCallback(() => {
		setRelationshipFilter(null);
	}, []);

	// Delete workflow handlers
	const handleDeleteWorkflow = useCallback(
		async (workflowId: string) => {
			setDeletingWorkflowId(workflowId);

			try {
				const response = await authFetch(
					`/api/workflows/${workflowId}`,
					{
						method: "DELETE",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({}),
					},
				);

				if (response.status === 409) {
					const conflict = await response.json();
					setPendingDeactivations(
						conflict.pending_deactivations ?? [],
					);
					setAvailableReplacements(
						conflict.available_replacements ?? [],
					);
					setDeleteDialogOpen(true);
				} else if (response.ok) {
					toast.success("Workflow deleted");
					refetchWorkflows();
					setDeletingWorkflowId(null);
				} else {
					const error = await response.json();
					toast.error(error.detail || "Failed to delete workflow");
					setDeletingWorkflowId(null);
				}
			} catch {
				toast.error("Failed to delete workflow");
				setDeletingWorkflowId(null);
			}
		},
		[refetchWorkflows],
	);

	const handleResolveDeletion = useCallback(
		async (body: {
			replacements?: Record<string, string>;
			force_deactivation?: boolean;
		}) => {
			const ids = conflictWorkflowIds.length
				? conflictWorkflowIds
				: deletingWorkflowId
					? [deletingWorkflowId]
					: [];
			const deleted: string[] = [];
			const failed: string[] = [];
			for (const id of ids) {
				try {
					const response = await authFetch(`/api/workflows/${id}`, {
						method: "DELETE",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify(body),
					});
					if (!response.ok) throw new Error("Deletion failed");
					deleted.push(id);
				} catch {
					failed.push(id);
				}
			}
			if (deleted.length) {
				void refetchWorkflows();
				setSelectedIds(
					(previous) =>
						new Set(
							[...previous].filter((id) => !deleted.includes(id)),
						),
				);
				toast.success(
					`Deleted ${deleted.length} workflow${deleted.length === 1 ? "" : "s"}`,
				);
			}
			if (failed.length) {
				setConflictWorkflowIds(failed);
				setPendingDeactivations((previous) =>
					previous.filter((item) => !deleted.includes(item.id)),
				);
				throw new Error(
					`${failed.length} workflow${failed.length === 1 ? " could" : "s could"} not be deleted. Your choices are preserved. Retry will only process the remaining workflows.`,
				);
			}
			setDeleteDialogOpen(false);
			setDeletingWorkflowId(null);
			setConflictWorkflowIds([]);
			setPendingDeactivations([]);
			setAvailableReplacements([]);
		},
		[conflictWorkflowIds, deletingWorkflowId, refetchWorkflows],
	);

	const handleCancelDelete = useCallback(() => {
		setDeleteDialogOpen(false);
		setDeletingWorkflowId(null);
		setConflictWorkflowIds([]);
		setPendingDeactivations([]);
		setAvailableReplacements([]);
	}, []);

	// Unified delete handler that dispatches by entity type
	const handleDeleteEntity = useCallback(
		(entityId: string, entityName: string, entityType: EntityType) => {
			if (
				allEntities.some(
					(entity) =>
						entity.id === entityId && isEntityManaged(entity),
				)
			)
				return;
			if (entityType === "workflow") {
				handleDeleteWorkflow(entityId);
				return;
			}
			const entity = allEntities.find((e) => e.id === entityId);
			const slug =
				entityType === "app" && entity
					? (entity.original as ApplicationPublic).slug
					: undefined;
			setConfirmDeleteEntities([
				{ id: entityId, name: entityName, entityType, slug },
			]);
			setDeleteFailures([]);
			setConfirmDeleteOpen(true);
		},
		[handleDeleteWorkflow, allEntities],
	);

	// Bulk delete handler
	const handleBulkDelete = useCallback(() => {
		const selectedEntities = allEntities.filter(
			(e) => selectedIds.has(e.id) && !isEntityManaged(e),
		);

		const entitiesToDelete = selectedEntities.map((e) => ({
			id: e.id,
			name: e.name,
			entityType: e.entityType,
			slug:
				e.entityType === "app"
					? (e.original as ApplicationPublic).slug
					: undefined,
		}));

		setConfirmDeleteEntities(entitiesToDelete);
		setDeleteFailures([]);
		setConfirmDeleteOpen(true);
	}, [allEntities, selectedIds]);

	// Execute confirmed deletes
	const handleConfirmDelete = useCallback(async () => {
		if (deleteBusy.current || !confirmDeleteEntities.length) return;
		deleteBusy.current = true;
		setIsDeleting(true);
		setDeleteFailures([]);
		try {
			const result = await deleteEntities(confirmDeleteEntities);
			if (result.conflictIds.length) {
				setConflictWorkflowIds(result.conflictIds);
				setPendingDeactivations(result.pendingDeactivations);
				setAvailableReplacements(result.availableReplacements);
				setDeleteDialogOpen(true);
			}
			if (result.deletedIds.length) {
				toast.success(
					`Deleted ${result.deletedIds.length} of ${confirmDeleteEntities.length} entities`,
				);
				void refetchForms();
				void refetchAgents();
				void refetchApps();
				void refetchWorkflows();
				setSelectedIds(
					(previous) =>
						new Set(
							[...previous].filter(
								(id) => !result.deletedIds.includes(id),
							),
						),
				);
			}
			setConfirmDeleteEntities(
				result.failures.map((failure) => failure.entity),
			);
			setDeleteFailures(result.failures);
			if (!result.failures.length) setConfirmDeleteOpen(false);
		} finally {
			deleteBusy.current = false;
			setIsDeleting(false);
		}
	}, [
		confirmDeleteEntities,
		refetchForms,
		refetchAgents,
		refetchApps,
		refetchWorkflows,
	]);

	const allSelected =
		filteredEntities.some((e) => !isEntityManaged(e)) &&
		filteredEntities
			.filter((e) => !isEntityManaged(e))
			.every((e) => selectedIds.has(e.id));
	const someSelected =
		filteredEntities.some((e) => selectedIds.has(e.id)) && !allSelected;

	const handleOrgDrop = useCallback(
		async (entityIds: string[], orgId: string | null) => {
			const failedNames: string[] = [];
			setUpdatingMessage("Applying changes...");
			setIsUpdating(true);
			try {
				for (const entityId of entityIds) {
					const entity = allEntities.find((e) => e.id === entityId);
					if (!entity || isEntityManaged(entity)) {
						failedNames.push(entity?.name ?? entityId);
						continue;
					}

					try {
						if (entity.entityType === "workflow") {
							await updateWorkflow.mutateAsync(entityId, {
								organization_id: orgId,
							});
						} else if (entity.entityType === "form") {
							await updateForm.mutateAsync({
								params: { path: { form_id: entityId } },
								body: {
									organization_id: orgId,
									clear_roles: false,
								},
							});
						} else if (entity.entityType === "agent") {
							await updateAgent.mutateAsync({
								params: { path: { agent_id: entityId } },
								body: {
									organization_id: orgId,
									clear_roles: false,
								},
							});
						} else if (entity.entityType === "app") {
							const app = entity.original as ApplicationPublic;
							await updateApplication.mutateAsync({
								params: { path: { app_id: app.id } },
								body: { scope: orgId ?? "global" },
							});
						}
					} catch {
						failedNames.push(entity.name);
					}
				}
				if (failedNames.length)
					throw new Error(
						`Could not update: ${failedNames.join(", ")}. Other changes may have been applied. Retry to apply the requested setting again.`,
					);
				toast.success(
					`Updated ${entityIds.length} ${entityIds.length === 1 ? "entity" : "entities"}`,
				);
			} finally {
				setIsUpdating(false);
			}
		},
		[
			allEntities,
			updateWorkflow,
			updateForm,
			updateAgent,
			updateApplication,
		],
	);

	const handleRoleDrop = useCallback(
		async (entityIds: string[], roleIdOrAccessLevel: string) => {
			const failedNames: string[] = [];
			setUpdatingMessage("Applying changes...");
			setIsUpdating(true);
			const isAccessLevel = roleIdOrAccessLevel === "authenticated";
			const isClearRoles = roleIdOrAccessLevel === "clear-roles";

			try {
				for (const entityId of entityIds) {
					const entity = allEntities.find((e) => e.id === entityId);
					if (!entity || isEntityManaged(entity)) {
						failedNames.push(entity?.name ?? entityId);
						continue;
					}

					try {
						if (!isAccessLevel && !isClearRoles)
							await assignEntityRole(
								entity.entityType,
								entityId,
								roleIdOrAccessLevel,
							);
						if (entity.entityType === "workflow") {
							if (isClearRoles) {
								await updateWorkflow.mutateAsync(entityId, {
									access_level: "role_based",
									clear_roles: true,
								});
							} else {
								await updateWorkflow.mutateAsync(entityId, {
									access_level: isAccessLevel
										? "authenticated"
										: "role_based",
								});
							}
						} else if (entity.entityType === "form") {
							if (isClearRoles) {
								await updateForm.mutateAsync({
									params: { path: { form_id: entityId } },
									body: {
										access_level: "role_based",
										clear_roles: true,
									},
								});
							} else {
								await updateForm.mutateAsync({
									params: { path: { form_id: entityId } },
									body: {
										access_level: isAccessLevel
											? "authenticated"
											: "role_based",
										clear_roles: false,
									},
								});
							}
						} else if (entity.entityType === "agent") {
							if (isClearRoles) {
								await updateAgent.mutateAsync({
									params: { path: { agent_id: entityId } },
									body: {
										access_level: "role_based",
										clear_roles: true,
									},
								});
							} else {
								await updateAgent.mutateAsync({
									params: { path: { agent_id: entityId } },
									body: {
										access_level: isAccessLevel
											? "authenticated"
											: "role_based",
										clear_roles: false,
									},
								});
							}
						} else if (entity.entityType === "app") {
							const app = entity.original as ApplicationPublic;
							if (isClearRoles) {
								await updateApplication.mutateAsync({
									params: { path: { app_id: app.id } },
									body: {
										access_level: "role_based",
										role_ids: [],
									},
								});
							} else {
								await updateApplication.mutateAsync({
									params: { path: { app_id: app.id } },
									body: {
										access_level: isAccessLevel
											? "authenticated"
											: "role_based",
										role_ids: isAccessLevel
											? []
											: undefined,
									},
								});
							}
						}
					} catch {
						failedNames.push(entity.name);
					}
				}
				if (failedNames.length)
					throw new Error(
						`Could not update: ${failedNames.join(", ")}. Other changes may have been applied. Retry to apply the requested setting again.`,
					);
				toast.success(
					`Updated ${entityIds.length} ${entityIds.length === 1 ? "entity" : "entities"}`,
				);
			} finally {
				setIsUpdating(false);
			}
		},
		[
			allEntities,
			assignEntityRole,
			updateWorkflow,
			updateForm,
			updateAgent,
			updateApplication,
		],
	);

	return (
		<div className="mx-auto flex min-h-full w-full max-w-[1600px] min-w-0 flex-col gap-6 xl:h-full xl:min-h-0">
			<ListPageHeader
				title="Entity Management"
				description="Manage organization and access settings for workflows, forms, agents, and apps"
				actions={
					<Button variant="outline" onClick={handleRefresh}>
						<RefreshCw className="size-4" />
						Refresh
					</Button>
				}
			/>

			<EntityCollectionStatus collections={collections} />

			{/* Main Content - Two Column Layout */}
			<div className="grid grid-cols-1 gap-6 xl:min-h-0 xl:flex-1 xl:grid-cols-5">
				{/* Left Column: Entities List */}
				<div className="flex min-h-0 min-w-0 flex-col xl:col-span-2">
					{/* Relationship Filter Banner */}
					{relationshipFilter && (
						<RelationshipFilterBanner
							entityName={relationshipFilter.entityName}
							isError={graphError}
							isFetching={fetchingGraph}
							hasData={!!graphData}
							onRetry={() => void refetchGraph()}
							onViewGraph={() => setIsGraphDialogOpen(true)}
							onClear={handleClearRelationshipFilter}
						/>
					)}

					<EntityListToolbar
						search={searchTerm}
						onSearch={setSearchTerm}
						allSelected={allSelected}
						someSelected={someSelected}
						onSelectAll={handleSelectAll}
						visibleCount={filteredEntities.length}
						selectedCount={selectedIds.size}
						hiddenSelectedCount={
							[...selectedIds].filter(
								(id) =>
									!filteredEntities.some(
										(entity) => entity.id === id,
									),
							).length
						}
						onClearSelection={() => setSelectedIds(new Set())}
						onDelete={handleBulkDelete}
						assignmentAction={
							<EntityAssignmentSheet
								entities={allEntities}
								selectedIds={selectedIds}
								organizations={organizations ?? []}
								roles={roles ?? []}
								disabled={isUpdating}
								onOrganization={handleOrgDrop}
								onAccess={handleRoleDrop}
							/>
						}
						busy={isUpdating}
						busyMessage={updatingMessage}
						sortBy={sortBy}
						onSortBy={setSortBy}
						ascending={sortAsc}
						onToggleDirection={() => setSortAsc((value) => !value)}
						filters={
							!relationshipFilter && (
								<FilterPopover
									typeFilter={typeFilter}
									setTypeFilter={setTypeFilter}
									orgFilter={orgFilter}
									setOrgFilter={setOrgFilter}
									accessFilter={accessFilter}
									setAccessFilter={setAccessFilter}
									usageFilter={usageFilter}
									setUsageFilter={setUsageFilter}
									organizations={organizations ?? []}
									activeFilterCount={activeFilterCount}
									onClearFilters={handleClearFilters}
								/>
							)
						}
					/>

					{/* Entity List */}
					<div className="min-w-0 xl:min-h-0 xl:flex-1 xl:overflow-y-auto">
						{(isLoading && allEntities.length === 0) ||
						(relationshipFilter && loadingGraph) ? (
							<div className="space-y-2">
								{[...Array(5)].map((_, i) => (
									<Skeleton key={i} className="h-16 w-full" />
								))}
							</div>
						) : relationshipFilter &&
						  graphError &&
						  !graphData ? null : filteredEntities.length > 0 ? (
							<div className="space-y-2 xl:pr-2">
								{filteredEntities.map((entity) => (
									<EntityCard
										key={`${entity.entityType}-${entity.id}`}
										entity={entity}
										selected={selectedIds.has(entity.id)}
										onSelect={(selected) =>
											handleSelectEntity(
												entity.id,
												selected,
											)
										}
										onShowRelationships={
											handleShowRelationships
										}
										onDelete={handleDeleteEntity}
										organizations={organizations ?? []}
										selectedIds={selectedIds}
										allEntities={allEntities}
									/>
								))}
							</div>
						) : incompleteEntityData || isLoading ? null : (
							<Card>
								<CardContent className="flex flex-col items-center justify-center py-12 text-center">
									<Filter className="h-12 w-12 text-muted-foreground" />
									<h3 className="mt-4 text-lg font-semibold">
										{relationshipFilter
											? "No related entities found"
											: searchTerm ||
												  activeFilterCount > 0
												? "No entities match your filters"
												: "No entities found"}
									</h3>
									<p className="mt-2 text-sm text-muted-foreground">
										{relationshipFilter
											? searchTerm
												? "No related entities match your search"
												: "No related entities are available in this list"
											: searchTerm ||
												  activeFilterCount > 0
												? "Try adjusting your filters"
												: "Create workflows, forms, or agents to manage them here"}
									</p>
								</CardContent>
							</Card>
						)}
					</div>
				</div>

				<div className="hidden min-w-0 flex-col xl:col-span-3 xl:flex xl:min-h-0 xl:overflow-auto">
					<EntityAssignmentPanel
						entities={allEntities}
						selectedIds={selectedIds}
						organizations={organizations ?? []}
						roles={roles ?? []}
						disabled={isUpdating}
						onOrganization={handleOrgDrop}
						onAccess={handleRoleDrop}
					/>
				</div>
			</div>

			{/* Dependency Graph Dialog */}
			<DependencyGraphDialog
				open={isGraphDialogOpen}
				onOpenChange={setIsGraphDialogOpen}
				entityName={relationshipFilter?.entityName ?? ""}
				entityType={relationshipFilter?.entityType ?? null}
				graphData={graphData ?? null}
				isLoading={loadingGraph}
				isError={graphError}
				isFetching={fetchingGraph}
				onRetry={() => void refetchGraph()}
			/>

			{/* Workflow Deactivation Dialog (for delete confirmation) */}
			<WorkflowDeactivationDialog
				pendingDeactivations={pendingDeactivations}
				availableReplacements={availableReplacements}
				open={deleteDialogOpen && !confirmDeleteOpen}
				onResolve={(replacements, workflowsToDeactivate) => {
					const hasReplacements =
						Object.keys(replacements).length > 0;
					const hasDeactivations = workflowsToDeactivate.length > 0;
					if (hasReplacements) {
						return handleResolveDeletion({ replacements });
					} else if (hasDeactivations) {
						return handleResolveDeletion({
							force_deactivation: true,
						});
					}
					return Promise.resolve();
				}}
				onCancel={handleCancelDelete}
			/>

			{/* Confirm Delete Dialog */}
			<DeleteConfirmDialog
				open={confirmDeleteOpen}
				onOpenChange={(open) => {
					if (!open && !deleteBusy.current) {
						setConfirmDeleteOpen(false);
						setConfirmDeleteEntities([]);
					}
				}}
				entities={confirmDeleteEntities}
				isDeleting={isDeleting}
				failures={deleteFailures}
				onConfirm={handleConfirmDelete}
				onCancel={() => {
					if (deleteBusy.current) return;
					setConfirmDeleteOpen(false);
					setConfirmDeleteEntities([]);
				}}
			/>
		</div>
	);
}
