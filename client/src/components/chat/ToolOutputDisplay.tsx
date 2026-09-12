// client/src/components/chat/ToolOutputDisplay.tsx
/**
 * ToolOutputDisplay Component
 *
 * Renders tool output text with pattern-based syntax highlighting.
 * Recognizes standard formats:
 * - Diff lines: +/- prefixes get green/red coloring
 * - Grep format: file:line: gets cyan coloring
 * - Status messages: Updated/Deleted/Created get blue coloring
 * - Errors: Error: prefix gets red coloring
 */

import { cn } from "@/lib/utils";

interface ToolOutputDisplayProps {
	text: string;
	className?: string;
}

/**
 * Determine CSS class for a line based on its content pattern.
 */
function getLineClass(line: string): string {
	// Diff format: added lines
	if (line.startsWith("+")) {
		return "text-[var(--bf-success)]";
	}

	// Diff format: removed lines
	if (line.startsWith("-")) {
		return "text-[var(--bf-danger)]";
	}

	// Grep format: file:line: match
	if (/^[\w./]+:\d+:/.test(line)) {
		return "text-[var(--bf-info)]";
	}

	// Status messages
	if (/^(Updated|Deleted|Created|Found)\s/.test(line)) {
		return "text-[var(--bf-info)]";
	}

	// Error messages
	if (line.startsWith("Error:") || line.startsWith("✗")) {
		return "text-[var(--bf-danger)]";
	}

	// Success indicators
	if (line.startsWith("✓")) {
		return "text-[var(--bf-success)]";
	}

	return "";
}

export function ToolOutputDisplay({
	text,
	className,
}: ToolOutputDisplayProps) {
	const lines = text.split("\n");

	return (
		<pre
			className={cn(
				"max-w-full overflow-x-auto rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 p-3 font-mono text-sm leading-6 whitespace-pre-wrap [overflow-wrap:anywhere]",
				className
			)}
		>
			{lines.map((line, i) => (
				<div key={i} className={cn("min-w-0", getLineClass(line))}>
					{line || "\u00A0"} {/* Non-breaking space for empty lines */}
				</div>
			))}
		</pre>
	);
}
