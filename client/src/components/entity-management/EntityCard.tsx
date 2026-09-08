import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
	GripVertical,
	Building2,
	Globe,
	Shield,
	Calendar,
	Network,
	Link,
	Trash2,
} from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { draggable } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { setCustomNativeDragPreview } from "@atlaskit/pragmatic-drag-and-drop/element/set-custom-native-drag-preview";
import { cn } from "@/lib/utils";
import { formatDateShort } from "@/lib/utils";
import type { EntityWithScope, EntityType, Organization } from "./types";
import { ENTITY_CONFIG, isEntityManaged } from "./types";

// Drag Preview Component
function DragPreview({
	count,
	entityName,
}: {
	count: number;
	entityName: string;
}) {
	return (
		<div className="flex items-center gap-2 rounded-[var(--bf-radius-surface)] bg-card shadow-lg ring-1 ring-foreground/5 dark:ring-foreground/10 px-3 py-2">
			<GripVertical className="h-4 w-4 text-muted-foreground" />
			<span className="font-medium">
				{count > 1 ? `${count} entities` : entityName}
			</span>
			{count > 1 && (
				<Badge variant="secondary" className="ml-1">
					{count}
				</Badge>
			)}
		</div>
	);
}

// Entity Card Component
export interface EntityCardProps {
	entity: EntityWithScope;
	selected: boolean;
	onSelect: (selected: boolean) => void;
	onShowRelationships: (
		entityId: string,
		entityType: EntityType,
		entityName: string,
	) => void;
	onDelete?: (
		entityId: string,
		entityName: string,
		entityType: EntityType,
	) => void;
	organizations: Organization[];
	selectedIds: Set<string>;
	allEntities: EntityWithScope[];
}

export function EntityCard({
	entity,
	selected,
	onSelect,
	onShowRelationships,
	onDelete,
	organizations,
	selectedIds,
	allEntities,
}: EntityCardProps) {
	const ref = useRef<HTMLDivElement>(null);
	const [dragging, setDragging] = useState(false);
	const [previewContainer, setPreviewContainer] =
		useState<HTMLElement | null>(null);

	const managed = isEntityManaged(entity);
	const config = ENTITY_CONFIG[entity.entityType];
	const Icon = config.icon;

	const orgName = entity.organizationId
		? (organizations.find((o) => o.id === entity.organizationId)?.name ??
			"Unknown Org")
		: "Global";

	// Calculate drag count for preview
	const dragCount = selected ? selectedIds.size : 1;

	useEffect(() => {
		const el = ref.current;
		if (!el || managed) return;

		return draggable({
			element: el,
			getInitialData: () => {
				const idsToMove = selected
					? allEntities
							.filter(
								(item) =>
									selectedIds.has(item.id) &&
									!isEntityManaged(item),
							)
							.map((item) => item.id)
					: [entity.id];

				return {
					type: "entity",
					entityIds: idsToMove,
					entityCount: idsToMove.length,
					entityTypes: idsToMove.map((id) => {
						const e = allEntities.find((ent) => ent.id === id);
						return e?.entityType ?? "unknown";
					}),
				};
			},
			onGenerateDragPreview: ({ nativeSetDragImage }) => {
				setCustomNativeDragPreview({
					nativeSetDragImage,
					render: ({ container }) => {
						setPreviewContainer(container);
					},
				});
			},
			onDragStart: () => setDragging(true),
			onDrop: () => {
				setDragging(false);
				setPreviewContainer(null);
			},
		});
	}, [entity.id, entity.name, selected, selectedIds, allEntities, managed]);

	return (
		<>
			<div
				ref={ref}
				className={cn(
					"flex items-start gap-3 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)] transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none",
					!managed && "cursor-grab active:cursor-grabbing",
					dragging && "opacity-50",
					selected
						? "border-primary bg-accent"
						: "bg-card hover:border-primary/50",
				)}
			>
				<Checkbox
					checked={selected && !managed}
					disabled={managed}
					onCheckedChange={onSelect}
					onClick={(e) => e.stopPropagation()}
					aria-label={`Select ${entity.name}`}
					className="mt-0.5"
				/>

				{!managed && (
					<GripVertical
						aria-hidden="true"
						className="hidden h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5 lg:block"
					/>
				)}

				<div className="flex-1 min-w-0 space-y-3">
					{/* Row 1: Name + Type badge + Actions */}
					<div className="flex flex-wrap items-center justify-between gap-2">
						<div className="flex min-w-0 basis-full items-start gap-2">
							<Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
							<p className="min-w-0 font-medium [overflow-wrap:anywhere]">
								{entity.name}
							</p>
						</div>
						<div className="flex flex-wrap items-center gap-1.5">
							<Badge
								variant="outline"
								className={cn(config.color)}
							>
								{config.label}
							</Badge>
							{managed && (
								<Badge variant="outline">
									Solution managed
								</Badge>
							)}
							<RecordActionsMenu
								label={`More actions for ${entity.name}`}
								contentClassName="w-max max-w-[calc(100vw-2rem)]"
							>
								<DropdownMenuItem
									className="whitespace-nowrap"
									onSelect={() =>
										onShowRelationships(
											entity.id,
											entity.entityType,
											entity.name,
										)
									}
								>
									<Network
										aria-hidden="true"
										className="size-4"
									/>
									Show dependencies
								</DropdownMenuItem>
								{onDelete && !managed && (
									<DropdownMenuItem
										variant="destructive"
										onSelect={() =>
											onDelete(
												entity.id,
												entity.name,
												entity.entityType,
											)
										}
									>
										<Trash2
											aria-hidden="true"
											className="size-4"
										/>
										Delete {config.label.toLowerCase()}
									</DropdownMenuItem>
								)}
							</RecordActionsMenu>
						</div>
					</div>

					{/* Row 2: Organization */}
					<div className="flex items-center gap-1 text-xs text-muted-foreground">
						{entity.organizationId ? (
							<Building2 className="h-3 w-3 shrink-0" />
						) : (
							<Globe className="h-3 w-3 shrink-0" />
						)}
						<span>{orgName}</span>
					</div>

					{/* Row 3: Access Level + Date + Used By Count */}
					<div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
						<span className="flex items-center gap-1">
							<Shield className="h-3 w-3 shrink-0" />
							{entity.accessLevel ?? "\u2014"}
						</span>
						<span className="flex items-center gap-1">
							<Calendar className="h-3 w-3 shrink-0" />
							{formatDateShort(entity.createdAt)}
						</span>
						{entity.usedByCount !== null && (
							<span
								className={cn(
									"flex items-center gap-1",
									entity.usedByCount === 0
										? "text-muted-foreground/50"
										: "text-muted-foreground",
								)}
							>
								<Link className="h-3 w-3 shrink-0" />
								{entity.entityType === "workflow"
									? entity.usedByCount === 0
										? "No refs"
										: `${entity.usedByCount} ref${entity.usedByCount === 1 ? "" : "s"}`
									: entity.usedByCount === 0
										? "No deps"
										: `Uses ${entity.usedByCount}`}
							</span>
						)}
					</div>
				</div>
			</div>
			{previewContainer &&
				createPortal(
					<DragPreview count={dragCount} entityName={entity.name} />,
					previewContainer,
				)}
		</>
	);
}
