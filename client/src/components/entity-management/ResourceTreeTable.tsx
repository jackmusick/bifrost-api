import { useMemo, useState } from "react";
import {
	Building2,
	Calendar,
	ChevronRight,
	Globe,
	Network,
	Shield,
	Trash2,
} from "lucide-react";

import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { cn, formatDateShort } from "@/lib/utils";
import type { DependencyGraph } from "@/hooks/useDependencyGraph";

import type { EntityType, EntityWithScope, Organization, Role } from "./types";
import { ENTITY_CONFIG, isEntityManaged, formatEntityAccess } from "./types";

interface ResourceTreeTableProps {
	entities: EntityWithScope[];
	organizations: Organization[];
	roles: Role[];
	selectedIds: Set<string>;
	allSelected: boolean;
	someSelected: boolean;
	onSelectAll: (selected: boolean) => void;
	onSelect: (entityId: string, selected: boolean) => void;
	onShowRelationships: (
		entityId: string,
		entityType: EntityType,
		entityName: string,
	) => void;
	onDelete: (
		entityId: string,
		entityName: string,
		entityType: EntityType,
	) => void;
	graphData?: DependencyGraph | null;
	focusedEntityId?: string | null;
}

interface ResourceRow {
	entity: EntityWithScope;
	depth: number;
	relationship?: string;
	expandable: boolean;
	expanded: boolean;
}

export function ResourceTreeTable({
	entities,
	organizations,
	roles,
	selectedIds,
	allSelected,
	someSelected,
	onSelectAll,
	onSelect,
	onShowRelationships,
	onDelete,
	graphData,
	focusedEntityId,
}: ResourceTreeTableProps) {
	const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
	const rows = useResourceRows(
		entities,
		graphData,
		focusedEntityId,
		expandedIds,
	);
	const toggleExpanded = (entityId: string) => {
		setExpandedIds((current) => {
			const next = new Set(current);
			if (next.has(entityId)) next.delete(entityId);
			else next.add(entityId);
			return next;
		});
	};

	return (
		<>
			<div className="hidden min-w-0 overflow-hidden rounded-[var(--bf-radius-surface)] border border-border bg-card lg:block">
				<table className="w-full table-fixed text-sm">
					<thead className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
						<tr>
							<th className="w-12 px-4 py-3">
								<Checkbox
									aria-label="Select all visible entities"
									checked={
										someSelected
											? "indeterminate"
											: allSelected
									}
									disabled={entities.length === 0}
									onCheckedChange={(value) =>
										onSelectAll(value === true)
									}
								/>
							</th>
							<th className="w-[52%] px-4 py-3">Resource</th>
							<th className="w-[18%] px-4 py-3">Scope</th>
							<th className="w-[18%] px-4 py-3">Access</th>
							<th className="w-16 px-4 py-3 text-right">
								<span className="sr-only">Actions</span>
							</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((row) => (
							<ResourceTableRow
								key={`${row.entity.entityType}:${row.entity.id}`}
								row={row}
								organizationName={organizationName(
									row.entity,
									organizations,
								)}
								accessName={accessName(row.entity, roles)}
								selected={selectedIds.has(row.entity.key)}
								onToggleExpanded={toggleExpanded}
								onSelect={onSelect}
								onShowRelationships={onShowRelationships}
								onDelete={onDelete}
							/>
						))}
					</tbody>
				</table>
			</div>

			<div className="grid gap-3 lg:hidden">
				{rows.map((row) => (
					<ResourceMobileCard
						key={`${row.entity.entityType}:${row.entity.id}`}
						row={row}
						organizationName={organizationName(
							row.entity,
							organizations,
						)}
						accessName={accessName(row.entity, roles)}
						selected={selectedIds.has(row.entity.key)}
						onToggleExpanded={toggleExpanded}
						onSelect={onSelect}
						onShowRelationships={onShowRelationships}
						onDelete={onDelete}
					/>
				))}
			</div>
		</>
	);
}

function ResourceTableRow({
	row,
	organizationName,
	accessName,
	selected,
	onToggleExpanded,
	onSelect,
	onShowRelationships,
	onDelete,
}: {
	row: ResourceRow;
	organizationName: string;
	accessName: string;
	selected: boolean;
	onToggleExpanded: (entityId: string) => void;
	onSelect: (entityId: string, selected: boolean) => void;
	onShowRelationships: ResourceTreeTableProps["onShowRelationships"];
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const { entity, depth, relationship, expandable, expanded } = row;
	const managed = isEntityManaged(entity);
	const config = ENTITY_CONFIG[entity.entityType];
	const Icon = config.icon;

	return (
		<tr
			className={cn(
				"border-b border-border/70 last:border-b-0",
				selected && !managed ? "bg-accent" : "hover:bg-muted/20",
			)}
		>
			<td className="px-4 py-4 align-top">
				<Checkbox
					aria-label={`Select ${entity.name}`}
					checked={selected && !managed}
					disabled={managed}
					onCheckedChange={(value) =>
						onSelect(entity.key, value === true)
					}
				/>
			</td>
			<td className="min-w-0 px-4 py-4 align-top">
				<div
					className="flex min-w-0 items-start gap-2"
					style={{ paddingLeft: `${depth * 1.25}rem` }}
				>
					<ExpandButton
						entityName={entity.name}
						expandable={expandable}
						expanded={expanded}
						onClick={() => onToggleExpanded(entity.key)}
					/>
					<div className="flex size-9 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] border border-border bg-background">
						<Icon className="size-4 text-muted-foreground" />
					</div>
					<ResourceLabel
						entity={entity}
						relationship={relationship}
					/>
				</div>
			</td>
			<td className="px-4 py-4 align-top text-sm">
				<ScopeText
					entity={entity}
					organizationName={organizationName}
				/>
			</td>
			<td className="px-4 py-4 align-top text-sm">
				<AccessText name={accessName} />
			</td>
			<td className="px-4 py-3 align-top">
				<RowActions
					entity={entity}
					managed={managed}
					onShowRelationships={onShowRelationships}
					onDelete={onDelete}
				/>
			</td>
		</tr>
	);
}

function ResourceMobileCard({
	row,
	organizationName,
	accessName,
	selected,
	onToggleExpanded,
	onSelect,
	onShowRelationships,
	onDelete,
}: {
	row: ResourceRow;
	organizationName: string;
	accessName: string;
	selected: boolean;
	onToggleExpanded: (entityId: string) => void;
	onSelect: (entityId: string, selected: boolean) => void;
	onShowRelationships: ResourceTreeTableProps["onShowRelationships"];
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const { entity, depth, relationship, expandable, expanded } = row;
	const managed = isEntityManaged(entity);
	const config = ENTITY_CONFIG[entity.entityType];
	const Icon = config.icon;

	return (
		<Card
			className={cn(
				"overflow-hidden",
				selected && !managed && "border-primary bg-accent",
			)}
			style={{ marginLeft: `${Math.min(depth, 2) * 0.75}rem` }}
		>
			<CardContent className="space-y-4 p-[var(--bf-surface-pad)]">
				<div className="flex min-w-0 items-start gap-2">
					<Checkbox
						aria-label={`Select ${entity.name}`}
						checked={selected && !managed}
						disabled={managed}
						onCheckedChange={(value) =>
							onSelect(entity.key, value === true)
						}
					/>
					<ExpandButton
						entityName={entity.name}
						expandable={expandable}
						expanded={expanded}
						onClick={() => onToggleExpanded(entity.key)}
					/>
					<Icon className="mt-1 size-4 shrink-0 text-muted-foreground" />
					<div className="min-w-0 flex-1">
						<ResourceLabel
							entity={entity}
							relationship={relationship}
						/>
					</div>
					<RowActions
						entity={entity}
						managed={managed}
						onShowRelationships={onShowRelationships}
						onDelete={onDelete}
					/>
				</div>
				<div className="grid gap-3 text-sm sm:grid-cols-2">
					<ScopeText
						entity={entity}
						organizationName={organizationName}
					/>
					<AccessText name={accessName} />
					<span className="flex items-center gap-2 text-muted-foreground">
						<Calendar className="size-4 shrink-0" />
						{formatDateShort(entity.createdAt)}
					</span>
				</div>
			</CardContent>
		</Card>
	);
}

function ExpandButton({
	entityName,
	expandable,
	expanded,
	onClick,
}: {
	entityName: string;
	expandable: boolean;
	expanded: boolean;
	onClick: () => void;
}) {
	return (
		<Button
			type="button"
			variant="ghost"
			size="icon-sm"
			className={cn("mt-1 size-7 shrink-0", !expandable && "invisible")}
			aria-label={`${expanded ? "Collapse" : "Expand"} ${entityName}`}
			aria-expanded={expandable ? expanded : undefined}
			disabled={!expandable}
			onClick={onClick}
		>
			<ChevronRight
				aria-hidden="true"
				className={cn(
					"size-4 transition-transform",
					expanded && "rotate-90",
				)}
			/>
		</Button>
	);
}

function ResourceLabel({
	entity,
	relationship,
}: {
	entity: EntityWithScope;
	relationship?: string;
}) {
	const config = ENTITY_CONFIG[entity.entityType];
	return (
		<div className="min-w-0 space-y-1">
			<div className="flex min-w-0 flex-wrap items-center gap-2">
				<p className="min-w-0 font-medium text-foreground [overflow-wrap:anywhere]">
					{entity.name}
				</p>
				<Badge variant="outline" className={config.color}>
					{config.label}
				</Badge>
				{isEntityManaged(entity) ? (
					<Badge variant="outline">Solution managed</Badge>
				) : null}
			</div>
			<p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
				{relationship ?? resourceUsageText(entity)}
			</p>
		</div>
	);
}

function RowActions({
	entity,
	managed,
	onShowRelationships,
	onDelete,
}: {
	entity: EntityWithScope;
	managed: boolean;
	onShowRelationships: ResourceTreeTableProps["onShowRelationships"];
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const config = ENTITY_CONFIG[entity.entityType];
	return (
		<div className="flex justify-end gap-1">
			<Button
				variant="ghost"
				size="icon-lg"
				aria-label={`Focus relationships for ${entity.name}`}
				title="Focus relationships"
				onClick={() =>
					onShowRelationships(
						entity.id,
						entity.entityType,
						entity.name,
					)
				}
			>
				<Network aria-hidden="true" className="size-4" />
			</Button>
			{!managed ? (
				<RecordActionsMenu label={`More actions for ${entity.name}`}>
					<DropdownMenuItem
						variant="destructive"
						onSelect={() =>
							onDelete(entity.id, entity.name, entity.entityType)
						}
					>
						<Trash2 aria-hidden="true" className="size-4" />
						Delete {config.label.toLowerCase()}
					</DropdownMenuItem>
				</RecordActionsMenu>
			) : null}
		</div>
	);
}

function ScopeText({
	entity,
	organizationName,
}: {
	entity: EntityWithScope;
	organizationName: string;
}) {
	return (
		<span className="flex min-w-0 items-center gap-2 text-foreground">
			{entity.organizationId ? (
				<Building2 className="size-4 shrink-0 text-muted-foreground" />
			) : (
				<Globe className="size-4 shrink-0 text-muted-foreground" />
			)}
			<span className="min-w-0 [overflow-wrap:anywhere]">
				{organizationName}
			</span>
		</span>
	);
}

function AccessText({ name }: { name: string }) {
	return (
		<span className="flex min-w-0 items-center gap-2 text-foreground">
			<Shield className="size-4 shrink-0 text-muted-foreground" />
			<span className="min-w-0 [overflow-wrap:anywhere]">{name}</span>
		</span>
	);
}

function organizationName(
	entity: EntityWithScope,
	organizations: Organization[],
) {
	return entity.organizationId
		? (organizations.find((org) => org.id === entity.organizationId)
				?.name ?? "Unknown organization")
		: "Global";
}

function accessName(entity: EntityWithScope, roles: Role[]) {
	if (entity.accessLevel === "role_based" && entity.roleIds.length > 0) {
		return entity.roleIds
			.map(
				(roleId) =>
					roles.find((role) => role.id === roleId)?.name ?? roleId,
			)
			.join(", ");
	}
	return formatEntityAccess(entity.accessLevel);
}

function resourceUsageText(entity: EntityWithScope) {
	if (entity.entityType === "app") return "App resource";
	if (entity.usedByCount === null) return "Relationship count unavailable";
	if (entity.entityType === "workflow") {
		return entity.usedByCount === 0
			? "No forms or agents use this workflow"
			: `Used by ${entity.usedByCount} resource${entity.usedByCount === 1 ? "" : "s"}`;
	}
	return entity.usedByCount === 0
		? "No workflow dependencies"
		: `Uses ${entity.usedByCount} workflow${entity.usedByCount === 1 ? "" : "s"}`;
}

function useResourceRows(
	entities: EntityWithScope[],
	graphData?: DependencyGraph | null,
	focusedEntityId?: string | null,
	expandedIds: Set<string> = new Set(),
): ResourceRow[] {
	return useMemo(() => {
		if (!graphData?.edges?.length || !focusedEntityId) {
			return entities.map((entity) => ({
				entity,
				depth: 0,
				expandable: false,
				expanded: false,
			}));
		}

		const byNodeId = new Map<string, EntityWithScope>();
		for (const entity of entities) {
			byNodeId.set(`${entity.entityType}:${entity.id}`, entity);
		}

		const neighbors = new Map<string, { id: string; caption: string }[]>();
		for (const edge of graphData.edges) {
			if (!byNodeId.has(edge.source) || !byNodeId.has(edge.target))
				continue;
			const source = byNodeId.get(edge.source);
			const target = byNodeId.get(edge.target);
			if (!source || !target) continue;
			const outgoing = neighbors.get(edge.source) ?? [];
			outgoing.push({
				id: edge.target,
				caption: relationshipCaption(
					edge.relationship,
					source.name,
					"out",
				),
			});
			neighbors.set(edge.source, outgoing);
			const incoming = neighbors.get(edge.target) ?? [];
			incoming.push({
				id: edge.source,
				caption: relationshipCaption(
					edge.relationship,
					target.name,
					"in",
				),
			});
			neighbors.set(edge.target, incoming);
		}

		const rootKey = graphData.root_id;
		const seen = new Set<string>();
		const rows: ResourceRow[] = [];

		const visit = (
			nodeId: string,
			depth: number,
			relationship?: string,
		) => {
			if (seen.has(nodeId)) return;
			const entity = byNodeId.get(nodeId);
			if (!entity) return;
			seen.add(nodeId);
			const childEdges = (neighbors.get(nodeId) ?? []).filter(
				(child) => !seen.has(child.id),
			);
			const expanded = !expandedIds.has(entity.key);
			rows.push({
				entity,
				depth,
				relationship,
				expandable: childEdges.length > 0,
				expanded,
			});
			if (expanded) {
				for (const child of childEdges) {
					visit(child.id, depth + 1, child.caption);
				}
			}
		};

		visit(rootKey, 0);
		return rows;
	}, [entities, graphData, focusedEntityId, expandedIds]);
}

function relationshipCaption(
	relationship: string,
	connectedName: string,
	direction: "out" | "in",
) {
	if (relationship === "uses") {
		return direction === "out"
			? `Used by ${connectedName}`
			: `Uses ${connectedName}`;
	}
	if (relationship === "used_by") {
		return direction === "out"
			? `Uses ${connectedName}`
			: `Used by ${connectedName}`;
	}
	return `${relationship
		.split("_")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ")} ${connectedName}`;
}
