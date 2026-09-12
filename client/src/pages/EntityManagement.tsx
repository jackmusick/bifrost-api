import { isEntityManaged } from "@/components/entity-management/types";
import { deleteEntities } from "@/components/entity-management/deleteEntities";
import { EntityCollectionStatus } from "@/components/entity-management/EntityCollectionStatus";
import { EntityListToolbar } from "@/components/entity-management/EntityListToolbar";
import { useAssignEntityRole } from "@/hooks/useAssignEntityRole";
import { EntityAssignmentPanel } from "@/components/entity-management/EntityAssignmentPanel";
import { ResourceTreeTable } from "@/components/entity-management/ResourceTreeTable";
import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { RefreshCw, Filter, GitBranch, Pencil, Trash2, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/PageLoader";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useWorkflows, useUpdateWorkflow } from "@/hooks/useWorkflows";
import { useForms, useUpdateForm } from "@/hooks/useForms";
import { useAgents, useUpdateAgent } from "@/hooks/useAgents";
import { useApplications, useUpdateApplication } from "@/hooks/useApplications";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useRoles } from "@/hooks/useRoles";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import { WorkflowDeactivationDialog } from "@/components/editor/WorkflowDeactivationDialog";
import { authFetch } from "@/lib/api-client";
import { useDependencyAvailability } from "@/services/dependencies";
import { toast } from "sonner";
import type { components } from "@/lib/v1";

import {
	FilterPopover,
	DeleteConfirmDialog,
	normalizeEntities,
	type EntityType,
	type EntityWithScope,
	type Organization,
	type Role,
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
	const [visibleEntityKeys, setVisibleEntityKeys] = useState<string[]>([]);
	const [connectedEntityKeys, setConnectedEntityKeys] = useState<string[]>(
		[],
	);
	const [connectedGraph, setConnectedGraph] = useState<{
		keys: string[];
		edges: { source: string; target: string }[];
	}>({ keys: [], edges: [] });
	const [isUpdating, setIsUpdating] = useState(false);
	const [updatingMessage, setUpdatingMessage] = useState("Updating...");

	const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
	const editReturnFocusRef = useRef<HTMLButtonElement | null>(null);
	const desktopEditorRef = useRef<HTMLElement | null>(null);
	const reduceMotion = useReducedMotion();
	const isDesktop = useIsDesktop();

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
	const initialSourceLoading = collections.some(
		(collection) => collection.isLoading,
	);
	const missingInitialSourceData = collections.some(
		(collection) => collection.isError && !collection.hasData,
	);

	// Normalize and combine all entities
	const normalizedEntities = useMemo(
		() =>
			normalizeEntities(
				workflows ?? [],
				forms ?? [],
				agents ?? [],
				appsResponse?.applications ?? [],
			),
		[workflows, forms, agents, appsResponse],
	);
	const availabilityRequest = useMemo(
		() => ({
			workflow_ids: normalizedEntities
				.filter((entity) => entity.entityType === "workflow")
				.map((entity) => entity.id),
			form_ids: normalizedEntities
				.filter((entity) => entity.entityType === "form")
				.map((entity) => entity.id),
			agent_ids: normalizedEntities
				.filter((entity) => entity.entityType === "agent")
				.map((entity) => entity.id),
			app_ids: normalizedEntities
				.filter((entity) => entity.entityType === "app")
				.map((entity) => entity.id),
		}),
		[normalizedEntities],
	);
	const availabilityQuery = useDependencyAvailability(
		availabilityRequest,
		!initialSourceLoading &&
			!missingInitialSourceData &&
			normalizedEntities.length > 0,
	);
	const relationshipAvailabilityKnown = availabilityQuery.data !== undefined;
	const isInitialRelationshipAvailabilityLoading =
		normalizedEntities.length > 0 &&
		availabilityQuery.data === undefined &&
		availabilityQuery.isLoading;
	const collectionsWithRelationships = [
		...collections,
		{
			name: "Relationships",
			isLoading: availabilityQuery.isLoading,
			isError: availabilityQuery.isError,
			isFetching: availabilityQuery.isFetching,
			hasData: availabilityQuery.data !== undefined,
			onRetry: () => void availabilityQuery.refetch(),
		},
	];

	const allEntities = useMemo(() => {
		const relationshipAvailability =
			availabilityQuery.data?.has_relationships ?? {};
		return normalizedEntities.map((entity) => ({
			...entity,
			hasRelationships: relationshipAvailabilityKnown
				? relationshipAvailability[entity.key] === true
				: false,
		}));
	}, [
		normalizedEntities,
		availabilityQuery.data,
		relationshipAvailabilityKnown,
	]);
	const isInitialEntityListLoading =
		!missingInitialSourceData &&
		(initialSourceLoading || isInitialRelationshipAvailabilityLoading);

	// Apply filters
	const filteredEntities = useMemo(() => {
		let result = allEntities;

		if (typeFilter !== "all") {
			result = result.filter((e) => e.entityType === typeFilter);
		}

		if (orgFilter !== "all") {
			if (orgFilter === "global") {
				result = result.filter((e) => !e.organizationId);
			} else {
				result = result.filter((e) => e.organizationId === orgFilter);
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
			} else if (usageFilter === "related_mismatch") {
				const byKey = new Map(
					allEntities.map((entity) => [entity.key, entity]),
				);
				const mismatchedKeys = new Set<string>();
				for (const edge of connectedGraph.edges) {
					const source = byKey.get(edge.source);
					const target = byKey.get(edge.target);
					if (!source || !target) continue;
					if (hasScopeOrAccessMismatch(source, target)) {
						mismatchedKeys.add(source.key);
						mismatchedKeys.add(target.key);
					}
				}
				result = result.filter((e) => mismatchedKeys.has(e.key));
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
		typeFilter,
		orgFilter,
		accessFilter,
		usageFilter,
		connectedGraph.edges,
		searchTerm,
		sortBy,
		sortAsc,
	]);

	const activeFilterCount =
		(typeFilter !== "all" ? 1 : 0) +
		(orgFilter !== "all" ? 1 : 0) +
		(accessFilter !== "all" ? 1 : 0) +
		(usageFilter !== "all" ? 1 : 0);

	const entitiesByKey = useMemo(
		() => new Map(allEntities.map((entity) => [entity.key, entity])),
		[allEntities],
	);
	const rootVisibleKeys = useMemo(
		() => filteredEntities.map((entity) => entity.key),
		[filteredEntities],
	);
	const effectiveVisibleKeys = useMemo(
		() =>
			filteredEntities.length === 0
				? []
				: visibleEntityKeys.length > 0
					? visibleEntityKeys
					: rootVisibleKeys,
		[filteredEntities.length, visibleEntityKeys, rootVisibleKeys],
	);
	const visibleKeySet = useMemo(
		() => new Set(effectiveVisibleKeys),
		[effectiveVisibleKeys],
	);
	const visibleSelectableKeys = useMemo(
		() =>
			effectiveVisibleKeys.filter((key) => {
				const entity = entitiesByKey.get(key);
				return entity && !isEntityManaged(entity);
			}),
		[effectiveVisibleKeys, entitiesByKey],
	);

	const allSelected =
		visibleSelectableKeys.length > 0 &&
		visibleSelectableKeys.every((key) => selectedIds.has(key));
	const someSelected =
		visibleSelectableKeys.some((key) => selectedIds.has(key)) &&
		!allSelected;
	const hiddenSelectedCount = [...selectedIds].filter(
		(key) => !visibleKeySet.has(key),
	).length;
	const connectedSelectableKeys = useMemo(
		() =>
			connectedEntityKeys.filter((key) => {
				const entity = entitiesByKey.get(key);
				return entity && !isEntityManaged(entity);
			}),
		[connectedEntityKeys, entitiesByKey],
	);
	const selectionSummary =
		selectedIds.size > 0
			? `${selectedIds.size} selected${
					hiddenSelectedCount > 0
						? ` (${hiddenSelectedCount} outside this view)`
						: ""
				}`
			: "No resources selected";

	useEffect(() => {
		if (!isDesktop || !isEditDrawerOpen || selectedIds.size === 0) return;
		window.requestAnimationFrame(() => {
			desktopEditorRef.current?.focus({ preventScroll: true });
		});
	}, [isDesktop, isEditDrawerOpen, selectedIds.size]);

	const handleVisibleKeysChange = useCallback((entityKeys: string[]) => {
		setVisibleEntityKeys((previous) =>
			previous.length === entityKeys.length &&
			previous.every((key, index) => key === entityKeys[index])
				? previous
				: entityKeys,
		);
	}, []);
	const handleConnectedKeysChange = useCallback((entityKeys: string[]) => {
		setConnectedEntityKeys((previous) =>
			previous.length === entityKeys.length &&
			previous.every((key, index) => key === entityKeys[index])
				? previous
				: entityKeys,
		);
	}, []);
	const handleConnectedGraphChange = useCallback(
		(graph: { keys: string[]; edges: { source: string; target: string }[] }) => {
			setConnectedGraph((previous) => {
				const sameKeys =
					previous.keys.length === graph.keys.length &&
					previous.keys.every((key, index) => key === graph.keys[index]);
				const sameEdges =
					previous.edges.length === graph.edges.length &&
					previous.edges.every(
						(edge, index) =>
							edge.source === graph.edges[index]?.source &&
							edge.target === graph.edges[index]?.target,
					);
				return sameKeys && sameEdges ? previous : graph;
			});
		},
		[],
	);

	const handleClearFilters = () => {
		setTypeFilter("all");
		setOrgFilter("all");
		setAccessFilter("all");
		setUsageFilter("all");
	};

	const handleRefresh = () => {
		void refetchOrganizations();
		void refetchRoles();
		void availabilityQuery.refetch();
		refetchWorkflows();
		refetchForms();
		refetchAgents();
		refetchApps();
	};

	const handleSelectEntity = (entityId: string, selected: boolean) => {
		const next = new Set(selectedIds);
		if (selected) next.add(entityId);
		else next.delete(entityId);
		setSelectedIds(next);
		if (!next.size) setIsEditDrawerOpen(false);
	};

	const handleSelectAll = (selected: boolean) => {
		const next = new Set(selectedIds);
		for (const key of visibleSelectableKeys) {
			if (selected) next.add(key);
			else next.delete(key);
		}
		setSelectedIds(next);
		if (!next.size) setIsEditDrawerOpen(false);
	};
	const clearSelection = () => {
		setSelectedIds(new Set());
		setIsEditDrawerOpen(false);
	};
	const handleSelectConnected = () => {
		setSelectedIds((previous) => {
			const next = new Set(previous);
			for (const key of connectedSelectableKeys) next.add(key);
			return next;
		});
	};
	const closeEditor = useCallback(() => {
		setIsEditDrawerOpen(false);
		window.requestAnimationFrame(() => {
			editReturnFocusRef.current?.focus({ preventScroll: true });
		});
	}, []);
	const openEditor = useCallback(() => {
		setIsEditDrawerOpen(true);
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
				setIsEditDrawerOpen(false);
				void refetchWorkflows();
				setSelectedIds(
					(previous) =>
						new Set(
							[...previous].filter(
								(key) =>
									!deleted.some(
										(id) => key === `workflow:${id}`,
									),
							),
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
						entity.id === entityId &&
						entity.entityType === entityType &&
						isEntityManaged(entity),
				)
			)
				return;
			if (entityType === "workflow") {
				handleDeleteWorkflow(entityId);
				return;
			}
			const entity = allEntities.find(
				(e) => e.id === entityId && e.entityType === entityType,
			);
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
			(e) => selectedIds.has(e.key) && !isEntityManaged(e),
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
				setIsEditDrawerOpen(false);
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
								(key) => !result.deletedKeys.includes(key),
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

	const handleOrgDrop = useCallback(
		async (entityIds: string[], orgId: string | null) => {
			const failedNames: string[] = [];
			setUpdatingMessage("Applying changes...");
			setIsUpdating(true);
			try {
				for (const entityId of entityIds) {
					const entity = allEntities.find((e) => e.key === entityId);
					if (!entity || isEntityManaged(entity)) {
						failedNames.push(entity?.name ?? entityId);
						continue;
					}

					try {
						if (entity.entityType === "workflow") {
							await updateWorkflow.mutateAsync(entity.id, {
								organization_id: orgId,
							});
						} else if (entity.entityType === "form") {
							await updateForm.mutateAsync({
								params: { path: { form_id: entity.id } },
								body: {
									organization_id: orgId,
									clear_roles: false,
								},
							});
						} else if (entity.entityType === "agent") {
							await updateAgent.mutateAsync({
								params: { path: { agent_id: entity.id } },
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
		async (
			entityIds: string[],
			change: {
				accessLevel?: string;
				addRoleId?: string;
				clearRoles?: boolean;
			},
		) => {
			const failedNames: string[] = [];
			const accessLevel = change.accessLevel;
			if (
				accessLevel !== undefined &&
				accessLevel !== "authenticated" &&
				accessLevel !== "everyone" &&
				accessLevel !== "role_based"
			) {
				throw new Error("Unsupported access level");
			}
			const addRoleId = change.addRoleId;
			const clearRoles = change.clearRoles === true;
			setUpdatingMessage("Applying changes...");
			setIsUpdating(true);

			try {
				for (const entityId of entityIds) {
					const entity = allEntities.find((e) => e.key === entityId);
					if (!entity || isEntityManaged(entity)) {
						failedNames.push(entity?.name ?? entityId);
						continue;
					}

					try {
						if (addRoleId && !entity.roleIds.includes(addRoleId)) {
							await assignEntityRole(
								entity.entityType,
								entity.id,
								addRoleId,
							);
						}
						if (entity.entityType === "workflow") {
							if (clearRoles) {
								await updateWorkflow.mutateAsync(entity.id, {
									access_level: accessLevel ?? "role_based",
									role_ids: [],
								});
							} else if (accessLevel || addRoleId) {
								await updateWorkflow.mutateAsync(entity.id, {
									access_level:
										accessLevel ??
										(addRoleId ? "role_based" : undefined),
								});
							}
						} else if (entity.entityType === "form") {
							if (clearRoles) {
								await updateForm.mutateAsync({
									params: { path: { form_id: entity.id } },
									body: {
										access_level: accessLevel ?? "role_based",
										role_ids: [],
										clear_roles: false,
									},
								});
							} else if (accessLevel || addRoleId) {
								await updateForm.mutateAsync({
									params: { path: { form_id: entity.id } },
									body: {
										access_level:
											accessLevel ??
											(addRoleId
												? "role_based"
												: undefined),
										clear_roles: false,
									},
								});
							}
						} else if (entity.entityType === "agent") {
							if (clearRoles) {
								await updateAgent.mutateAsync({
									params: { path: { agent_id: entity.id } },
									body: {
										access_level: accessLevel ?? "role_based",
										role_ids: [],
										clear_roles: false,
									},
								});
							} else if (accessLevel || addRoleId) {
								await updateAgent.mutateAsync({
									params: { path: { agent_id: entity.id } },
									body: {
										access_level:
											accessLevel ??
											(addRoleId
												? "role_based"
												: undefined),
										clear_roles: false,
									},
								});
							}
						} else if (entity.entityType === "app") {
							const app = entity.original as ApplicationPublic;
							if (clearRoles) {
								await updateApplication.mutateAsync({
									params: { path: { app_id: app.id } },
									body: {
										access_level: accessLevel ?? "role_based",
										role_ids: [],
									},
								});
							} else if (accessLevel || addRoleId) {
								await updateApplication.mutateAsync({
									params: { path: { app_id: app.id } },
									body: {
										access_level:
											accessLevel ??
											(addRoleId
												? "role_based"
												: undefined),
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
		<div className="mx-auto flex min-h-full w-full max-w-[1180px] min-w-0 flex-col gap-6 xl:h-full xl:min-h-0">
			<ListPageHeader
				title="Entity Management"
				description="Find connected resources. Manage scope and access together."
				actions={
					<Button variant="outline" onClick={handleRefresh}>
						<RefreshCw className="size-4" />
						Refresh
					</Button>
				}
			/>

			<EntityCollectionStatus
				collections={collectionsWithRelationships}
			/>

			<section
				aria-label="Resource directory"
				className="flex min-w-0 flex-col rounded-[var(--bf-radius-surface)] border border-border bg-card xl:min-h-0 xl:flex-1 xl:overflow-hidden"
			>
				<EntityListToolbar
					search={searchTerm}
					onSearch={setSearchTerm}
					allSelected={allSelected}
					someSelected={someSelected}
					onSelectAll={handleSelectAll}
					visibleCount={effectiveVisibleKeys.length}
					selectedCount={selectedIds.size}
					hiddenSelectedCount={hiddenSelectedCount}
					onClearSelection={clearSelection}
					onDelete={handleBulkDelete}
					onEditSelection={openEditor}
					busy={isUpdating}
					busyMessage={updatingMessage}
					sortBy={sortBy}
					onSortBy={setSortBy}
					ascending={sortAsc}
					onToggleDirection={() => setSortAsc((value) => !value)}
					filters={
						<>
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
							<Button
								type="button"
								variant="outline"
								size="lg"
								disabled={
									isUpdating ||
									connectedSelectableKeys.length === 0
								}
								onClick={handleSelectConnected}
							>
								<GitBranch
									aria-hidden="true"
									className="size-4"
								/>
								Select connected
							</Button>
						</>
					}
				/>

				<div className="relative min-w-0 xl:flex xl:min-h-0 xl:flex-1 xl:overflow-hidden">
					<div className="min-w-0 xl:flex-1 xl:overflow-y-auto">
						{isInitialEntityListLoading ? (
							<PageLoader message="Loading entities…" size="sm" />
						) : filteredEntities.length > 0 ? (
							<ResourceTreeTable
								entities={filteredEntities}
								allEntities={allEntities}
								organizations={organizations ?? []}
								roles={roles ?? []}
								selectedIds={selectedIds}
								allSelected={allSelected}
								someSelected={someSelected}
								onSelectAll={handleSelectAll}
								onSelect={handleSelectEntity}
								onVisibleKeysChange={handleVisibleKeysChange}
								onConnectedKeysChange={
									handleConnectedKeysChange
								}
								onConnectedGraphChange={
									handleConnectedGraphChange
								}
								onDelete={handleDeleteEntity}
							/>
						) : incompleteEntityData || isLoading ? null : (
							<Card className="m-3">
								<CardContent className="flex flex-col items-center justify-center py-12 text-center">
									<Filter className="h-12 w-12 text-muted-foreground" />
									<h3 className="mt-4 text-lg font-semibold">
										{searchTerm || activeFilterCount > 0
											? "No entities match your filters"
											: "No entities found"}
									</h3>
									<p className="mt-2 text-sm text-muted-foreground">
										{searchTerm || activeFilterCount > 0
											? "Try adjusting your filters"
											: "Create workflows, forms, or agents to manage them here"}
									</p>
								</CardContent>
							</Card>
						)}
					</div>

					{isDesktop ? (
						<AnimatePresence initial={false}>
							{isEditDrawerOpen && selectedIds.size > 0 ? (
								<motion.aside
									key="entity-bulk-editor"
									role="dialog"
									aria-modal="false"
									tabIndex={-1}
									ref={desktopEditorRef}
									aria-label={`Edit ${selectedIds.size} ${
										selectedIds.size === 1
											? "resource"
											: "resources"
									}`}
									className="hidden min-w-0 shrink-0 flex-col overflow-hidden border-l border-border bg-card xl:flex"
									initial={
										reduceMotion
											? false
											: { width: 0, opacity: 0 }
									}
									animate={{ width: 416, opacity: 1 }}
									exit={{ width: 0, opacity: 0 }}
									transition={
										reduceMotion
											? { duration: 0 }
											: {
													duration: 0.2,
													ease: "easeInOut",
												}
									}
									onKeyDown={(event) => {
										if (event.key === "Escape") {
											event.stopPropagation();
											closeEditor();
										}
									}}
								>
									<BulkEditInspector
										selectedCount={selectedIds.size}
										entities={allEntities}
										selectedIds={selectedIds}
										organizations={organizations ?? []}
										roles={roles ?? []}
										disabled={isUpdating}
										onOrganization={handleOrgDrop}
										onAccess={handleRoleDrop}
										onClose={closeEditor}
									/>
								</motion.aside>
							) : null}
						</AnimatePresence>
					) : null}
				</div>

				<footer className="flex min-h-14 shrink-0 flex-col gap-2 border-t border-border bg-muted/20 px-3 py-2 text-sm sm:flex-row sm:items-center">
					<p
						role="status"
						className="min-w-0 flex-1 text-muted-foreground"
					>
						{isUpdating ? updatingMessage : selectionSummary}
					</p>
					{selectedIds.size > 0 ? (
						<div className="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-none sm:flex sm:flex-wrap sm:items-center">
							<Button
								type="button"
								size="lg"
								className="w-full sm:w-auto"
								disabled={isUpdating}
								onClick={openEditor}
								ref={editReturnFocusRef}
							>
								<Pencil aria-hidden="true" className="size-4" />
								Edit selected
							</Button>
							<Button
								type="button"
								variant="outline"
								size="lg"
								className="w-full sm:w-auto"
								disabled={isUpdating}
								onClick={clearSelection}
							>
								Clear
							</Button>
							<Button
								type="button"
								variant="outline"
								size="lg"
								className="w-full text-destructive sm:w-auto"
								disabled={isUpdating}
								onClick={handleBulkDelete}
							>
								<Trash2 aria-hidden="true" className="size-4" />
								Delete selected
							</Button>
						</div>
					) : null}
				</footer>
			</section>

			<Sheet
				open={!isDesktop && isEditDrawerOpen && selectedIds.size > 0}
				onOpenChange={(open) => {
					if (open) {
						openEditor();
					} else if (!isUpdating) {
						closeEditor();
					}
				}}
			>
				<SheetContent className="flex w-full flex-col overflow-hidden xl:hidden sm:max-w-xl">
					<SheetHeader className="border-b border-border">
						<SheetTitle>
							Edit {selectedIds.size}{" "}
							{selectedIds.size === 1 ? "resource" : "resources"}
						</SheetTitle>
						<SheetDescription>
							Only selected resources will change.
						</SheetDescription>
					</SheetHeader>
					<div className="min-h-0 flex-1 overflow-y-auto p-6">
						<EntityAssignmentPanel
							hideInstructions
							entities={allEntities}
							selectedIds={selectedIds}
							organizations={organizations ?? []}
							roles={roles ?? []}
							disabled={isUpdating}
							onOrganization={handleOrgDrop}
							onAccess={handleRoleDrop}
						/>
					</div>
				</SheetContent>
			</Sheet>

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

function BulkEditInspector({
	selectedCount,
	entities,
	selectedIds,
	organizations,
	roles,
	disabled,
	onOrganization,
	onAccess,
	onClose,
}: {
	selectedCount: number;
	entities: EntityWithScope[];
	selectedIds: Set<string>;
	organizations: Organization[];
	roles: Role[];
	disabled: boolean;
	onOrganization: (
		ids: string[],
		organizationId: string | null,
	) => Promise<void>;
	onAccess: (
		ids: string[],
		change: {
			accessLevel?: string;
			addRoleId?: string;
			clearRoles?: boolean;
		},
	) => Promise<void>;
	onClose: () => void;
}) {
	return (
		<>
			<header className="flex shrink-0 items-start gap-3 border-b border-border bg-card px-4 py-3">
				<div className="min-w-0 flex-1">
					<h2 className="text-sm font-semibold">
						Edit {selectedCount}{" "}
						{selectedCount === 1 ? "resource" : "resources"}
					</h2>
					<p className="text-xs text-muted-foreground">
						Only selected resources will change.
					</p>
				</div>
				<Button
					type="button"
					variant="ghost"
					size="icon-sm"
					aria-label="Close"
					disabled={disabled}
					onClick={onClose}
				>
					<X aria-hidden="true" className="size-4" />
				</Button>
			</header>
			<div className="min-h-0 flex-1 overflow-y-auto bg-card p-4">
				<EntityAssignmentPanel
					hideInstructions
					entities={entities}
					selectedIds={selectedIds}
					organizations={organizations}
					roles={roles}
					disabled={disabled}
					onOrganization={onOrganization}
					onAccess={onAccess}
				/>
			</div>
		</>
	);
}

function hasScopeOrAccessMismatch(
	entity: EntityWithScope,
	related: EntityWithScope,
) {
	return (
		entity.organizationId !== related.organizationId ||
		entity.accessLevel !== related.accessLevel ||
		normalizedRoleSignature(entity.roleIds) !==
			normalizedRoleSignature(related.roleIds)
	);
}

function normalizedRoleSignature(roleIds: string[]) {
	return [...roleIds].sort().join("\u0000");
}
