import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export function logSeverity(level?: string | null) {
	const normalized = level?.toLowerCase() ?? "info";
	if (["error", "critical", "fatal", "traceback"].includes(normalized))
		return { label: "Error", color: "var(--bf-danger)" };
	if (["warn", "warning"].includes(normalized))
		return { label: "Warning", color: "var(--bf-warning)" };
	if (["debug", "trace"].includes(normalized))
		return { label: "Debug", color: "var(--muted-foreground)" };
	return { label: "Info", color: "var(--bf-info)" };
}

/** Severity framing shared by readable activity and detailed execution logs. */
export function LogEntryRow({
	as: Tag = "div",
	level,
	style,
	className,
	children,
	...props
}: HTMLAttributes<HTMLElement> & { as?: "div" | "li"; level?: string | null }) {
	const severity = logSeverity(level);
	return (
		<Tag
			{...props}
			className={cn(className, "px-4")}
			data-severity={severity.label.toLowerCase()}
			style={{
				...style,
				borderInlineStart: `3px solid ${severity.color}`,
			}}
		>
			{children}
		</Tag>
	);
}
