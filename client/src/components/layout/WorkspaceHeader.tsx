import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Stable navigation band shared by a workspace directory and its detail views. */
export function WorkspaceHeader({
	className,
	...props
}: ComponentProps<"div">) {
	return (
		<div
			{...props}
			data-workspace-header
			className={cn(
				"flex h-12 min-h-12 shrink-0 items-stretch border-b border-border/70 bg-muted/10",
				className,
			)}
		/>
	);
}
