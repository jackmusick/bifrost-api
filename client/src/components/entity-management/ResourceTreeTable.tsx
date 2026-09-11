import { useEffect, useMemo, useState } from "react";
import {
	Building2,
	Calendar,
	ChevronRight,
	Globe,
	Shield,
	Trash2,
} from "lucide-react";

import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import {
	useDependencyGraph,
	type EntityType as DependencyEntityType,
	type DependencyGraph,
} from "@/hooks/useDependencyGraph";
import { cn, formatDateShort } from "@/lib/utils";

import type { EntityType, EntityWithScope, Organization, Role } from "./types";
import { ENTITY_CONFIG, formatEntityAccess, isEntityManaged } from "./types";

interface ResourceTreeTableProps {
	entities: EntityWithScope[];
	allEntities: EntityWithScope[];
	organizations: Organization[];
	roles: Role[];
	selectedIds: Set<string>;
	allSelected: boolean;
	someSelected: boolean;
	onSelectAll: (selected: boolean) => void;
	onSelect: (entityKey: string, selected: boolean) => void;
	onVisibleKeysChange?: (entityKeys: string[]) => void;
	onDelete: (
		entityId: string,
		entityName: string,
		entityType: EntityType,
	) => void;
}

interface ResourceRow {
	entity: EntityWithScope;
	depth: number;
	caption?: string;
	isLoading?: boolean;
	isError?: boolean;
	onRetry?: () => void;
	expandable: boolean;
	expanded: boolean;
}

export function ResourceTreeTable({
	entities,
	allEntities,
	organizations,
	roles,
	selectedIds,
	allSelected,
	someSelected,
	onSelectAll,
	onSelect,
	onVisibleKeysChange,
	onDelete,
}: ResourceTreeTableProps) {
	const [expandedKey, setExpandedKey] = useState<string | null>(null);
	const expandedEntity = allEntities.find((entity) => entity.key === expandedKey);
	const {
		data: graphData,
		isLoading,
		isError,
		isFetching,
		refetch,
	} = useDependencyGraph(
		expandedEntity?.entityType as DependencyEntityType | undefined,
		expandedEntity?.id,
		3,
	);
	const rows = useResourceRows({
		rootEntities: entities,
		allEntities,
		expandedKey,
		graphData: graphData ?? null,
		isLoading: isLoading || isFetching,
		isError,
		onRetry: () => void refetch(),
	});
	const visibleKeys = useMemo(
		() => Array.from(new Set(rows.map((row) => row.entity.key))),
		[rows],
	);
	const visibleKeySignature = visibleKeys.join("\u0000");

	useEffect(() => {
		onVisibleKeysChange?.(visibleKeys);
		// visibleKeySignature intentionally gates updates so callers receive
		// row visibility changes without a parent/child render loop.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [onVisibleKeysChange, visibleKeySignature]);

	const toggleExpanded = (entityKey: string) => {
		setExpandedKey((current) => (current === entityKey ? null : entityKey));
	};

	return (
		<>
			<div className="hidden min-w-0 overflow-hidden rounded-[var(--bf-radius-surface)] border border-border bg-card lg:block">
				<table className="w-full table-fixed text-sm">
					<thead className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
						<tr>
							<th className="w-10 px-3 py-2">
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
							<th className="w-[54%] px-3 py-2">Resource</th>
							<th className="w-[18%] px-3 py-2">Scope</th>
							<th className="w-[18%] px-3 py-2">Access</th>
							<th className="w-12 px-3 py-2 text-right">
								<span className="sr-only">Actions</span>
							</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((row) => (
							<ResourceTableRow
								key={`${row.entity.key}:${row.depth}:${row.caption ?? "root"}`}
								row={row}
								organizationName={organizationName(
									row.entity,
									organizations,
								)}
								accessName={accessName(row.entity, roles)}
								selected={selectedIds.has(row.entity.key)}
								onToggleExpanded={toggleExpanded}
								onSelect={onSelect}
								onDelete={onDelete}
							/>
						))}
					</tbody>
				</table>
			</div>

			<div className="grid gap-2 lg:hidden">
				{rows.map((row) => (
					<ResourceMobileCard
						key={`${row.entity.key}:${row.depth}:${row.caption ?? "root"}`}
						row={row}
						organizationName={organizationName(
							row.entity,
							organizations,
						)}
						accessName={accessName(row.entity, roles)}
						selected={selectedIds.has(row.entity.key)}
						onToggleExpanded={toggleExpanded}
						onSelect={onSelect}
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
	onDelete,
}: {
	row: ResourceRow;
	organizationName: string;
	accessName: string;
	selected: boolean;
	onToggleExpanded: (entityKey: string) => void;
	onSelect: (entityKey: string, selected: boolean) => void;
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const { entity, depth, caption, expandable, expanded, isLoading, isError } =
		row;
	const managed = isEntityManaged(entity);
	const config = ENTITY_CONFIG[entity.entityType];
	const Icon = config.icon;

	return (
		<tr
			className={cn(
				"border-b border-border/60 last:border-b-0",
				selected && !managed ? "bg-accent" : "hover:bg-muted/20",
			)}
		>
			<td className="px-3 py-2 align-middle">
				<Checkbox
					aria-label={`Select ${entity.name}`}
					checked={selected && !managed}
					disabled={managed}
					onCheckedChange={(value) =>
						onSelect(entity.key, value === true)
					}
				/>
			</td>
			<td className="min-w-0 px-3 py-2 align-middle">
				<div
					className="flex min-w-0 items-center gap-2"
					style={{ paddingLeft: `${depth * 1.1}rem` }}
				>
					<ExpandButton
						entityName={entity.name}
						expandable={expandable}
						expanded={expanded}
						loading={isLoading}
						onClick={() => onToggleExpanded(entity.key)}
					/>
					<div className="flex size-8 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] border border-border bg-background">
						<Icon className="size-4 text-muted-foreground" />
					</div>
					<ResourceLabel
						entity={entity}
						caption={
								isError
									? "Could not load related resources"
									: caption
						}
						onRetry={row.onRetry}
					/>
				</div>
			</td>
			<td className="px-3 py-2 align-middle text-sm">
				<ScopeText
					entity={entity}
					organizationName={organizationName}
				/>
			</td>
			<td className="px-3 py-2 align-middle text-sm">
				<AccessText name={accessName} />
			</td>
			<td className="px-3 py-2 align-middle">
				<RowActions entity={entity} managed={managed} onDelete={onDelete} />
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
	onDelete,
}: {
	row: ResourceRow;
	organizationName: string;
	accessName: string;
	selected: boolean;
	onToggleExpanded: (entityKey: string) => void;
	onSelect: (entityKey: string, selected: boolean) => void;
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const { entity, depth, caption, expandable, expanded, isLoading, isError } =
		row;
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
			<CardContent className="space-y-3 p-3">
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
						loading={isLoading}
						onClick={() => onToggleExpanded(entity.key)}
					/>
					<Icon className="mt-1 size-4 shrink-0 text-muted-foreground" />
					<div className="min-w-0 flex-1">
						<ResourceLabel
							entity={entity}
							caption={
									isError
										? "Could not load related resources"
										: caption
							}
							onRetry={row.onRetry}
						/>
					</div>
					<RowActions entity={entity} managed={managed} onDelete={onDelete} />
				</div>
				<div className="grid gap-2 text-sm sm:grid-cols-2">
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
	loading,
	onClick,
}: {
	entityName: string;
	expandable: boolean;
	expanded: boolean;
	loading?: boolean;
	onClick: () => void;
}) {
	return (
		<Button
			type="button"
			variant="ghost"
			size="icon-sm"
			className="size-7 shrink-0"
			aria-label={`${expanded ? "Collapse" : "Expand"} ${entityName}`}
			aria-expanded={expanded}
			onClick={onClick}
		>
			<ChevronRight
				aria-hidden="true"
				className={cn(
					"size-4 transition-transform",
					expanded && "rotate-90",
					loading && "animate-pulse",
					!expandable && !expanded && "opacity-45",
				)}
			/>
		</Button>
	);
}

function ResourceLabel({
	entity,
	caption,
	onRetry,
}: {
	entity: EntityWithScope;
	caption?: string;
	onRetry?: () => void;
}) {
	const config = ENTITY_CONFIG[entity.entityType];
	return (
		<div className="min-w-0">
			<div className="flex min-w-0 flex-wrap items-center gap-2">
				<p className="min-w-0 font-medium leading-5 text-foreground [overflow-wrap:anywhere]">
					{entity.name}
				</p>
				<Badge variant="outline" className={cn("h-5 px-1.5", config.color)}>
					{config.label}
				</Badge>
				{isEntityManaged(entity) ? (
					<Badge variant="outline" className="h-5 px-1.5">
						Solution managed
					</Badge>
				) : null}
			</div>
			<p className="flex flex-wrap items-center gap-2 text-xs leading-5 text-muted-foreground [overflow-wrap:anywhere]">
				<span>{caption ?? resourceUsageText(entity)}</span>
				{onRetry ? (
					<Button
						type="button"
						variant="link"
						size="sm"
						className="h-auto p-0 text-xs"
						onClick={onRetry}
					>
						Retry
					</Button>
				) : null}
			</p>
		</div>
	);
}

function RowActions({
	entity,
	managed,
	onDelete,
}: {
	entity: EntityWithScope;
	managed: boolean;
	onDelete: ResourceTreeTableProps["onDelete"];
}) {
	const config = ENTITY_CONFIG[entity.entityType];
	return !managed ? (
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
	) : null;
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

function useResourceRows({
	rootEntities,
	allEntities,
	expandedKey,
	graphData,
	isLoading,
	isError,
	onRetry,
}: {
	rootEntities: EntityWithScope[];
	allEntities: EntityWithScope[];
	expandedKey: string | null;
	graphData: DependencyGraph | null;
	isLoading: boolean;
	isError: boolean;
	onRetry?: () => void;
}): ResourceRow[] {
	return useMemo(() => {
		const rows: ResourceRow[] = [];
		const byKey = new Map(allEntities.map((entity) => [entity.key, entity]));
		for (const entity of rootEntities) {
			const expanded = expandedKey === entity.key;
			const childRows =
				expanded && !isLoading && !isError && graphData
					? relatedRows(entity, graphData, byKey)
					: [];
			rows.push({
				entity,
				depth: 0,
				caption: expanded
					? isLoading
						? "Loading related resources..."
						: isError
							? "Could not load related resources"
							: graphData && childRows.length === 0
								? "No related resources"
								: undefined
					: undefined,
				expandable: true,
				expanded,
				isLoading: expanded && isLoading,
				isError: expanded && isError,
				onRetry: expanded && isError ? onRetry : undefined,
			});
			if (!expanded || isLoading || isError || !graphData) continue;
			for (const child of childRows) {
				rows.push(child);
			}
		}
		return rows;
	}, [
		rootEntities,
		allEntities,
		expandedKey,
		graphData,
		isLoading,
		isError,
		onRetry,
	]);
}

function relatedRows(
	root: EntityWithScope,
	graphData: DependencyGraph,
	byKey: Map<string, EntityWithScope>,
) {
	const neighbors = new Map<string, { key: string; caption: string }[]>();
	for (const edge of graphData.edges ?? []) {
		const source = byKey.get(edge.source);
		const target = byKey.get(edge.target);
		if (!source || !target) continue;
		const outgoing = neighbors.get(edge.source) ?? [];
		outgoing.push({
			key: edge.target,
			caption: relationshipCaption(edge.relationship, source.name, "out"),
		});
		neighbors.set(edge.source, outgoing);
		const incoming = neighbors.get(edge.target) ?? [];
		incoming.push({
			key: edge.source,
			caption: relationshipCaption(edge.relationship, target.name, "in"),
		});
		neighbors.set(edge.target, incoming);
	}

	const rows: ResourceRow[] = [];
	const seen = new Set([root.key]);
	const visit = (key: string, depth: number, caption: string) => {
		if (seen.has(key)) return;
		const entity = byKey.get(key);
		if (!entity) return;
		seen.add(key);
		rows.push({
			entity,
			depth,
			caption,
			expandable: false,
			expanded: false,
		});
		for (const child of neighbors.get(key) ?? []) {
			visit(child.key, depth + 1, child.caption);
		}
	};
	for (const child of neighbors.get(root.key) ?? []) {
		visit(child.key, 1, child.caption);
	}
	return rows;
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
