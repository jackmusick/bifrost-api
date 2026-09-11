import { Workflow, FileText, Bot, AppWindow } from "lucide-react";
import type { components } from "@/lib/v1";

export type WorkflowMetadata = components["schemas"]["WorkflowMetadata"];
export type FormPublic = components["schemas"]["FormPublic"];
export type AgentSummary = components["schemas"]["AgentSummary"];
export type ApplicationPublic = components["schemas"]["ApplicationPublic"];
export type Organization = components["schemas"]["OrganizationPublic"];
export type Role = components["schemas"]["RolePublic"];

// Unified entity type for the management view
export type EntityType = "workflow" | "form" | "agent" | "app";

export interface EntityWithScope {
	key: string;
	id: string;
	name: string;
	entityType: EntityType;
	organizationId: string | null;
	accessLevel: string | null;
	roleIds: string[];
	createdAt: string;
	usedByCount: number | null; // null means count not available for this entity type
	hasRelationships: boolean;
	original: WorkflowMetadata | FormPublic | AgentSummary | ApplicationPublic;
}

// Sort options
export type SortOption = "name" | "date" | "type";

// Helper to normalize entities into unified format
export function normalizeEntities(
	workflows: WorkflowMetadata[] = [],
	forms: FormPublic[] = [],
	agents: AgentSummary[] = [],
	apps: ApplicationPublic[] = [],
): EntityWithScope[] {
	const entities: EntityWithScope[] = [];

	for (const w of workflows) {
		entities.push({
			key: entityKey("workflow", w.id),
			id: w.id,
			name: w.name,
			entityType: "workflow",
			organizationId: w.organization_id ?? null,
			accessLevel: w.access_level ?? null,
			roleIds: w.role_ids ?? [],
			createdAt: w.created_at,
			usedByCount: w.used_by_count ?? 0,
			hasRelationships: hasRelationships(w),
			original: w,
		});
	}

	for (const f of forms) {
		if (!f.is_active) continue;
		entities.push({
			key: entityKey("form", f.id),
			id: f.id,
			name: f.name,
			entityType: "form",
			organizationId: f.organization_id ?? null,
			accessLevel: f.access_level ?? null,
			roleIds: f.role_ids ?? [],
			createdAt: f.created_at ?? new Date().toISOString(),
			usedByCount: f.dependency_count ?? null,
			hasRelationships: hasRelationships(f),
			original: f,
		});
	}

	for (const a of agents) {
		if (!a.is_active || !a.id) continue;
		entities.push({
			key: entityKey("agent", a.id),
			id: a.id,
			name: a.name,
			entityType: "agent",
			organizationId:
				(a as { organization_id?: string | null }).organization_id ??
				null,
			accessLevel:
				(a as { access_level?: string | null }).access_level ?? null,
			roleIds: a.role_ids ?? [],
			createdAt: a.created_at,
			usedByCount: a.dependency_count ?? null,
			hasRelationships: hasRelationships(a),
			original: a,
		});
	}

	for (const app of apps) {
		entities.push({
			key: entityKey("app", app.id),
			id: app.id,
			name: app.name,
			entityType: "app",
			organizationId: app.organization_id ?? null,
			accessLevel: app.access_level ?? null,
			roleIds: app.role_ids ?? [],
			createdAt: app.created_at ?? new Date().toISOString(),
			usedByCount: null,
			hasRelationships: hasRelationships(app),
			original: app,
		});
	}

	return entities;
}

export function entityKey(entityType: EntityType, id: string) {
	return `${entityType}:${id}`;
}

function hasRelationships(
	entity: WorkflowMetadata | FormPublic | AgentSummary | ApplicationPublic,
) {
	return (
		(entity as { has_relationships?: boolean }).has_relationships === true
	);
}

// Entity type icons and colors
export const ENTITY_CONFIG = {
	workflow: {
		icon: Workflow,
		color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
		label: "Workflow",
	},
	form: {
		icon: FileText,
		color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
		label: "Form",
	},
	agent: {
		icon: Bot,
		color: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
		label: "Agent",
	},
	app: {
		icon: AppWindow,
		color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
		label: "App",
	},
} as const;

/** Solution deployment owns changes to these records. */
export function isEntityManaged(entity: EntityWithScope): boolean {
	const source = entity.original;
	if (!source) return false;
	return (
		("is_solution_managed" in source &&
			source.is_solution_managed === true) ||
		("solution_id" in source && !!source.solution_id)
	);
}

export function formatEntityAccess(accessLevel: string | null) {
	switch (accessLevel) {
		case "authenticated":
			return "Everyone except external users";
		case "role_based":
			return "Restricted to roles";
		case "private":
			return "Private";
		default:
			return "Not set";
	}
}
