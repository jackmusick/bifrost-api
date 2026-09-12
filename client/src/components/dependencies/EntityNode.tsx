/**
 * EntityNode - Custom React Flow node for dependency graph
 *
 * Displays an entity (workflow, form, app, agent) as a styled card
 * with color-coding by entity type.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
	Workflow,
	FileText,
	LayoutGrid,
	Bot,
	type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type EntityType = "workflow" | "form" | "app" | "agent";

export const ENTITY_TYPE_THEME = {
	workflow: {
		label: "Workflow",
		accent: "var(--chart-1)",
		accentSoft: "color-mix(in srgb, var(--chart-1) 14%, var(--background))",
		accentBorder: "color-mix(in srgb, var(--chart-1) 34%, var(--border))",
		iconColor: "var(--chart-1)",
		Icon: Workflow,
	},
	form: {
		label: "Form",
		accent: "var(--chart-2)",
		accentSoft: "color-mix(in srgb, var(--chart-2) 14%, var(--background))",
		accentBorder: "color-mix(in srgb, var(--chart-2) 34%, var(--border))",
		iconColor: "var(--chart-2)",
		Icon: FileText,
	},
	app: {
		label: "App",
		accent: "var(--chart-4)",
		accentSoft: "color-mix(in srgb, var(--chart-4) 14%, var(--background))",
		accentBorder: "color-mix(in srgb, var(--chart-4) 34%, var(--border))",
		iconColor: "var(--chart-4)",
		Icon: LayoutGrid,
	},
	agent: {
		label: "Agent",
		accent: "var(--chart-5)",
		accentSoft: "color-mix(in srgb, var(--chart-5) 14%, var(--background))",
		accentBorder: "color-mix(in srgb, var(--chart-5) 34%, var(--border))",
		iconColor: "var(--chart-5)",
		Icon: Bot,
	},
} satisfies Record<
	EntityType,
	{
		label: string;
		accent: string;
		accentSoft: string;
		accentBorder: string;
		iconColor: string;
		Icon: LucideIcon;
	}
>;

export interface EntityNodeData extends Record<string, unknown> {
	label: string;
	entityType: EntityType;
	orgId: string | null;
	isRoot: boolean;
}

function EntityNodeComponent({ data, selected }: NodeProps) {
	const nodeData = data as EntityNodeData;
	const config = ENTITY_TYPE_THEME[nodeData.entityType];
	const Icon = config.Icon;

	return (
		<div
			className={cn(
				"min-w-[180px] max-w-[250px] rounded-[var(--bf-radius-surface)] border px-4 py-3 transition-colors duration-150 motion-reduce:transition-none",
				"text-foreground",
				selected &&
					"ring-2 ring-primary ring-offset-2 ring-offset-background",
				nodeData.isRoot &&
					"ring-2 ring-primary ring-offset-1 ring-offset-background",
			)}
			style={{
				backgroundColor: config.accentSoft,
				borderColor: config.accentBorder,
			}}
		>
			{/* Handles for connections */}
			<Handle
				type="target"
				position={Position.Top}
				className="!w-2 !h-2"
				style={{ backgroundColor: config.accent }}
			/>
			<Handle
				type="source"
				position={Position.Bottom}
				className="!w-2 !h-2"
				style={{ backgroundColor: config.accent }}
			/>

			{/* Entity type badge */}
			<div className="flex items-center gap-2 mb-2">
				<div
					className={cn(
						"flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
					)}
					style={{
						backgroundColor: config.accentSoft,
						color: "var(--foreground)",
					}}
				>
					<Icon className="h-3 w-3" />
					<span>{config.label}</span>
				</div>
				{nodeData.isRoot && (
					<span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary text-primary-foreground">
						Root
					</span>
				)}
			</div>

			{/* Entity name */}
			<div
				className="font-medium text-sm text-foreground truncate"
				title={nodeData.label}
			>
				{nodeData.label}
			</div>

			{/* Organization indicator */}
			{nodeData.orgId && (
				<div className="mt-1 text-[10px] text-muted-foreground truncate">
					Org: {nodeData.orgId.slice(0, 8)}...
				</div>
			)}
			{!nodeData.orgId && (
				<div className="mt-1 text-[10px] text-muted-foreground">
					Global
				</div>
			)}
		</div>
	);
}

export const EntityNode = memo(EntityNodeComponent);
