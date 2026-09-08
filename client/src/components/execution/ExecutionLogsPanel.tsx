import { useRef, useEffect, useCallback, useMemo, useState } from "react";
import { ArrowDown, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { copyToClipboard } from "@/lib/clipboard";
import { toast } from "sonner";
import type { components } from "@/lib/v1";
import type { StreamingLog } from "@/stores/executionStreamStore";

// Re-export from generated types
export type ExecutionStatus = components["schemas"]["ExecutionStatus"];
export type ExecutionLogPublic = components["schemas"]["ExecutionLogPublic"];

// Union type that handles both API logs and streaming logs
export type LogEntry = ExecutionLogPublic | StreamingLog;

interface ExecutionLogsPanelProps {
	/** Logs to display (already merged/deduped by parent) */
	logs?: LogEntry[];
	/** Current execution status */
	status?: ExecutionStatus;
	/** Whether the WebSocket connection is active */
	isConnected?: boolean;
	/** Whether logs are still loading from API */
	isLoading?: boolean;
	/** Whether the user is a platform admin (shows DEBUG logs) */
	isPlatformAdmin?: boolean;
	/** Optional className for the panel */
	className?: string;
	/** Maximum height for the logs container */
	maxHeight?: string;
}

const levelColors: Record<string, string> = {
	debug: "text-muted-foreground",
	info: "text-[var(--bf-info)]",
	warning: "text-[var(--bf-warning)]",
	error: "text-[var(--bf-danger)]",
	traceback: "text-[var(--bf-danger)]",
};

/**
 * A renderable unit: either a single log line, or a run of consecutive
 * TRACEBACK lines coalesced into one block. A Python traceback arrives
 * as N separate log entries; rendering it as N rows (each repeating
 * timestamp + level) destroys scannability — it is ONE artifact.
 */
type LogRenderItem =
	| { kind: "line"; log: LogEntry }
	| { kind: "traceback"; timestamp?: string | null; lines: string[] };

export function coalesceTracebacks(logs: LogEntry[]): LogRenderItem[] {
	const items: LogRenderItem[] = [];
	for (const log of logs) {
		const isTraceback = log.level?.toLowerCase() === "traceback";
		const last = items[items.length - 1];
		if (isTraceback && last?.kind === "traceback") {
			last.lines.push(log.message || "");
		} else if (isTraceback) {
			items.push({
				kind: "traceback",
				timestamp: log.timestamp,
				lines: [log.message || ""],
			});
		} else {
			items.push({ kind: "line", log });
		}
	}
	return items;
}

function formatLogTime(timestamp?: string | null): string {
	return timestamp ? new Date(timestamp).toLocaleTimeString() : "";
}

export function ExecutionLogsPanel({
	logs = [],
	status,
	isConnected,
	isLoading = false,
	isPlatformAdmin = false,
	className,
	maxHeight = "600px",
}: ExecutionLogsPanelProps) {
	const logsContainerRef = useRef<HTMLDivElement>(null);
	const [autoScroll, setAutoScroll] = useState(true);
	const [copied, setCopied] = useState(false);

	const isRunning =
		status === "Running" || status === "Pending" || status === "Cancelling";
	const isComplete =
		status === "Success" ||
		status === "Failed" ||
		status === "CompletedWithErrors" ||
		status === "Timeout" ||
		status === "Cancelled";

	// Parent (ExecutionDetails) already merges API + streaming logs via
	// mergeLogsWithDedup and memoizes the array, so `logs` is a stable input.
	const renderItems = useMemo(() => coalesceTracebacks(logs), [logs]);

	// Auto-scroll to bottom when new logs arrive.
	// Uses scrollTop instead of scrollIntoView to avoid scrolling the outer page.
	useEffect(() => {
		const container = logsContainerRef.current;
		if (autoScroll && container && logs.length > 0) {
			container.scrollTop = container.scrollHeight;
		}
	}, [logs.length, autoScroll]);

	// Handle scroll to detect if user has scrolled up (pause auto-scroll)
	const handleLogsScroll = useCallback(() => {
		const container = logsContainerRef.current;
		if (!container) return;

		// Check if scrolled to bottom (with 50px threshold)
		const isAtBottom =
			container.scrollHeight -
				container.scrollTop -
				container.clientHeight <
			50;
		setAutoScroll(isAtBottom);
	}, []);

	const handleCopyLogs = useCallback(async () => {
		const text = logs
			.map((log) => {
				const time = formatLogTime(log.timestamp);
				const level = (log.level || "INFO").toUpperCase();
				return `${time}  ${level}  ${log.message || ""}`;
			})
			.join("\n");
		const copied = await copyToClipboard(text);
		if (copied) {
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} else {
			toast.error("Failed to copy logs");
		}
	}, [logs]);

	const copyButton = logs.length > 0 && (
		<Button
			variant="ghost"
			size="icon-lg"
			onClick={handleCopyLogs}
			title="Copy logs"
			aria-label={copied ? "Logs copied" : "Copy logs"}
		>
			{copied ? (
				<Check className="h-3.5 w-3.5 text-[var(--bf-success)]" />
			) : (
				<Copy className="h-3.5 w-3.5" />
			)}
		</Button>
	);

	const renderItem = (item: LogRenderItem, index: number) => {
		if (item.kind === "traceback") {
			return (
				<div
					key={index}
					className="grid min-w-0 grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-b border-border/50 px-3 py-3 text-xs font-mono last:border-0 @2xl:grid-cols-[auto_70px_minmax(0,1fr)] @2xl:py-1.5 hover:bg-muted/40"
					data-testid="log-traceback-block"
				>
					<span className="whitespace-nowrap tabular-nums text-muted-foreground">
						{formatLogTime(item.timestamp)}
					</span>
					<span
						className={`min-w-0 font-semibold uppercase ${levelColors.traceback}`}
					>
						traceback
					</span>
					<pre className="col-span-full min-w-0 whitespace-pre-wrap text-sm leading-relaxed [overflow-wrap:anywhere] @2xl:col-span-1 @2xl:text-xs">
						{item.lines.join("\n")}
					</pre>
				</div>
			);
		}

		const log = item.log;
		const level = log.level?.toLowerCase() || "info";
		const levelColor = levelColors[level] || "text-muted-foreground";
		// data field only exists on ExecutionLogPublic, not StreamingLog
		const data = "data" in log ? log.data : undefined;

		return (
			<div
				key={index}
				className="grid min-w-0 grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-b border-border/50 px-3 py-3 text-xs font-mono last:border-0 @2xl:grid-cols-[auto_70px_minmax(0,1fr)] @2xl:py-1.5 hover:bg-muted/40"
			>
				<span className="whitespace-nowrap tabular-nums text-muted-foreground">
					{formatLogTime(log.timestamp)}
				</span>
				<span
					className={`min-w-0 font-semibold uppercase ${levelColor}`}
				>
					{log.level}
				</span>
				<span data-testid="log-message" className="col-span-full min-w-0 whitespace-pre-wrap text-sm leading-relaxed [overflow-wrap:anywhere] @2xl:col-span-1 @2xl:text-xs">
					{log.message}
				</span>
				{data && Object.keys(data).length > 0 && (
					<details className="col-span-full min-w-0 text-xs @2xl:col-start-3">
						<summary className="min-h-11 cursor-pointer content-center text-muted-foreground">
							data
						</summary>
						<pre className="mt-1 min-w-0 whitespace-pre-wrap rounded-[var(--bf-radius-control)] bg-muted p-2 [overflow-wrap:anywhere]">
							{JSON.stringify(data, null, 2)}
						</pre>
					</details>
				)}
			</div>
		);
	};

	const renderLogList = () => (
		<div
			ref={logsContainerRef}
			onScroll={handleLogsScroll}
			className="min-w-0 overflow-y-auto py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
			aria-label="Execution log messages"
			role="region"
			tabIndex={0}
			style={{ maxHeight }}
		>
			{renderItems.map(renderItem)}
		</div>
	);

	const lineCount = logs.length;
	const countLabel = `${lineCount} line${lineCount !== 1 ? "s" : ""}`;

	// Inspector panel: one step-1 surface framed by a hairline ring, with a
	// step-2 header band — same idiom in the drawer and the details page.
	const logsContent =
		logs.length === 0 && !isLoading ? (
			<div className="text-center text-sm text-muted-foreground py-8">
				{isRunning
					? "Waiting for logs..."
					: isComplete
						? "No logs captured"
						: "No execution in progress"}
			</div>
		) : isLoading && logs.length === 0 ? (
			<div role="status" aria-label="Loading execution logs" className="space-y-2 p-4">
				<Skeleton className="h-3 w-full" />
				<Skeleton className="h-3 w-5/6" />
				<Skeleton className="h-3 w-4/5" />
			</div>
		) : (
			renderLogList()
		);

	return (
		<div
			className={cn(
				"@container min-w-0 overflow-hidden rounded-[var(--bf-radius-surface)] border border-border bg-muted/50",
				className,
			)}
		>
			{/* Header band (step-2) */}
			<div className="flex items-center justify-between gap-3 border-b border-border/50 bg-muted px-3 py-2">
				<div className="flex min-w-0 flex-wrap items-center gap-2">
					<span className="text-sm font-medium">Logs</span>
					{lineCount > 0 && (
						<span className="text-xs text-muted-foreground">
							{countLabel}
							{!isPlatformAdmin && " · INFO and above"}
						</span>
					)}
					{isConnected && isRunning && (
			<Badge variant="secondary" className="gap-1 text-xs">
				<span
					data-testid="execution-live-indicator"
					aria-hidden="true"
					className="h-2 w-2 rounded-full bg-[image:var(--bf-activity-gradient)] motion-safe:animate-pulse motion-reduce:animate-none"
				/>
				Live
			</Badge>
		)}
				</div>
				{copyButton}
			</div>
			{isRunning && isConnected === false && (
				<p role="status" className="border-b border-border/50 bg-[var(--bf-warning-soft)] px-3 py-3 text-sm text-foreground">
					Live connection unavailable. New log messages may be delayed.
				</p>
			)}
			{/* Content */}
			{logsContent}
			{!autoScroll && logs.length > 0 && (
				<div className="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-muted px-3 py-2">
					<span role="status" className="text-xs text-muted-foreground">Following paused</span>
					<Button variant="outline" className="min-h-11" onClick={() => setAutoScroll(true)}><ArrowDown className="h-4 w-4" />Jump to latest</Button>
				</div>
			)}
		</div>
	);
}
