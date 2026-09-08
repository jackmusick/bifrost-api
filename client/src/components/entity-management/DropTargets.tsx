import { useState, useEffect, useRef } from "react";
import { Globe, Building2, Shield, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { cn } from "@/lib/utils";
import type { Organization, Role } from "./types";

interface AssignmentTargetProps {
	name: string;
	icon: LucideIcon;
	selectedIds: string[];
	disabled?: boolean;
	onChoose: (ids: string[]) => void;
}

/** Dragging and native button activation enter the same review flow. */
function AssignmentTarget({ name, icon: Icon, selectedIds, disabled, onChoose }: AssignmentTargetProps) {
	const ref = useRef<HTMLDivElement>(null);
	const [dragCount, setDragCount] = useState(0);
	useEffect(() => {
		if (!ref.current) return;
		return dropTargetForElements({
			element: ref.current,
			canDrop: ({ source }) => !disabled && source.data["type"] === "entity",
			onDragEnter: ({ source }) => setDragCount(Number(source.data["entityCount"]) || 1),
			onDragLeave: () => setDragCount(0),
			onDrop: ({ source }) => {
				setDragCount(0);
				if (!disabled) onChoose(source.data["entityIds"] as string[]);
			},
		});
	}, [disabled, onChoose]);
	return (
		<div ref={ref} className={cn("flex flex-wrap items-center gap-2 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)] transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none", dragCount ? "border-primary bg-accent" : "bg-card")}>
			<Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
			<span className="min-w-0 flex-1 text-sm font-medium [overflow-wrap:anywhere]">{name}</span>
			<Button type="button" variant="outline" className="min-h-11" disabled={disabled || selectedIds.length === 0} onClick={() => onChoose([...selectedIds])} aria-label={`Apply ${name} to ${selectedIds.length} selected entities`}>
				Apply{selectedIds.length > 0 ? ` (${selectedIds.length})` : ""}
			</Button>
			{dragCount > 0 && <p role="status" className="basis-full text-sm text-muted-foreground">Drop to review changes to {dragCount} {dragCount === 1 ? "entity" : "entities"}.</p>}
		</div>
	);
}

interface TargetSelectionProps {
	selectedIds: string[];
	disabled?: boolean;
}
export interface OrgDropTargetProps extends TargetSelectionProps {
	organization: Organization | null;
	onDrop: (entityIds: string[], orgId: string | null) => void;
}
export function OrgDropTarget({ organization, onDrop, ...selection }: OrgDropTargetProps) {
	return <AssignmentTarget {...selection} name={organization?.name ?? "Global"} icon={organization ? Building2 : Globe} onChoose={(ids) => onDrop(ids, organization?.id ?? null)} />;
}
export interface RoleDropTargetProps extends TargetSelectionProps {
	role: Role | "authenticated" | "clear-roles";
	onDrop: (entityIds: string[], roleOrAccessLevel: string) => void;
}
export function RoleDropTarget({ role, onDrop, ...selection }: RoleDropTargetProps) {
	const name = role === "authenticated" ? "Everyone except external users" : role === "clear-roles" ? "Clear roles" : role.name;
	const id = typeof role === "string" ? role : role.id;
	return <AssignmentTarget {...selection} name={name} icon={Shield} onChoose={(ids) => onDrop(ids, id)} />;
}
