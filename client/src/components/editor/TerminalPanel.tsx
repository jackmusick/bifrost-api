import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	ArrowDown,
	Terminal as TerminalIcon,
	Trash2,
} from "lucide-react";
import { useEditorStore } from "@/stores/editorStore";
import { useExecutionStreamStore } from "@/stores/executionStreamStore";
import { Button } from "@/components/ui/button";
import { TerminalLogMessage } from "./TerminalLogMessage";
import { TerminalExecutionResult } from "./TerminalExecutionResult";

interface TerminalPanelProps {
	onResizeStart?: (e: React.MouseEvent) => void;
}

/**
 * Terminal panel for viewing execution logs
 * Displays output from script/workflow/data provider executions
 */
export function TerminalPanel({ onResizeStart }: TerminalPanelProps) {
	const terminalOutput = useEditorStore((state) => state.terminalOutput);
	const clearTerminalOutput = useEditorStore(
		(state) => state.clearTerminalOutput,
	);
	const currentStreamingExecutionId = useEditorStore(
		(state) => state.currentStreamingExecutionId,
	);

	// Get streaming logs from execution stream store
	// Use stable selector to only re-render when logs actually change
	const streamState = useExecutionStreamStore((state) =>
		currentStreamingExecutionId
			? state.streams[currentStreamingExecutionId]
			: undefined,
	);
	const streamingLogs = useMemo(
		() => streamState?.streamingLogs ?? [],
		[streamState?.streamingLogs],
	);

	const scrollRef = useRef<HTMLDivElement>(null);
	const [followLatest, setFollowLatest] = useState(true);

	const formatTimestamp = (isoString: string) => {
		const date = new Date(isoString);
		return date.toLocaleTimeString("en-US", {
			hour12: false,
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit",
		});
	};

	const getLogColor = (level: string) => {
		const upperLevel = level.toUpperCase();
		switch (upperLevel) {
			case "ERROR":
				return "text-[color:var(--bf-danger)]";
			case "WARNING":
				return "text-[color:var(--bf-warning)]";
			case "TRACEBACK":
				return "text-[color:var(--bf-danger)]";
			case "SUCCESS":
				return "text-[color:var(--bf-success)]";
			case "INFO":
			case "DEBUG":
			default:
				return "text-foreground";
		}
	};

	const hasTerminalContent =
		streamingLogs.length > 0 ||
		(terminalOutput?.executions.length ?? 0) > 0;
	const isStreamingActive = Boolean(
		currentStreamingExecutionId &&
			streamState &&
			!streamState.isComplete,
	);

	const scrollToLatest = useCallback(
		(behavior: ScrollBehavior = "auto") => {
			const container = scrollRef.current;
			if (!container) return;

			container.scrollTo({
				top: container.scrollHeight,
				behavior,
			});
		},
		[],
	);

	const handleScroll = useCallback(() => {
		const container = scrollRef.current;
		if (!container) return;

		const isAtBottom =
			container.scrollHeight -
				container.scrollTop -
				container.clientHeight <= 8;
		setFollowLatest(isAtBottom);
	}, []);

	useEffect(() => {
		if (!hasTerminalContent || !followLatest) return;
		scrollToLatest("auto");
	}, [
		hasTerminalContent,
		followLatest,
		scrollToLatest,
		streamingLogs.length,
		terminalOutput?.executions.length,
	]);

	const showJumpToLatest = hasTerminalContent && !followLatest;

	return (
		<div className="@container flex h-full min-w-0 flex-col overflow-hidden relative bg-background">
			{/* Resize handle */}
			<div
				className="absolute top-0 left-0 right-0 hidden h-1 cursor-row-resize transition-colors hover:bg-primary/50 active:bg-primary lg:block z-20"
				aria-hidden="true"
				onMouseDown={onResizeStart}
			/>

			{/* Loading bar - shown when execution is in progress */}
			{isStreamingActive && (
				<div
					className="absolute top-1 left-0 right-0 h-0.5 overflow-hidden bg-muted z-10"
					data-testid="terminal-loading-bar"
				>
					<div className="h-full bg-[image:var(--bf-activity-gradient)] animate-[loading_1.6s_ease-in-out_infinite] motion-reduce:animate-none" />
				</div>
			)}

			{/* Header with clear button */}
			{hasTerminalContent && (
				<div className="flex items-center justify-between gap-2 border-b bg-muted/30 px-3 py-1">
					<div className="flex items-center gap-2">
						<TerminalIcon className="h-3 w-3 text-muted-foreground" />
						<span className="text-xs font-medium text-muted-foreground">
							Terminal
						</span>
					</div>
					<div className="flex items-center gap-1">
						{showJumpToLatest && (
								<Button
									variant="outline"
									size="sm"
									onClick={() => {
										setFollowLatest(true);
										scrollToLatest("auto");
									}}
								className="h-8 gap-1.5 px-2.5"
								aria-label="Jump to latest terminal output"
							>
								<ArrowDown className="h-3 w-3" />
								<span className="text-xs">Jump to latest</span>
							</Button>
						)}
						<Button
							variant="ghost"
							size="sm"
							onClick={clearTerminalOutput}
							className="h-8 gap-1.5 px-2.5"
							title="Clear terminal output"
							aria-label="Clear terminal output"
						>
							<Trash2 className="h-3 w-3" />
							<span className="text-xs">Clear</span>
						</Button>
					</div>
				</div>
			)}

			{/* Terminal content */}
			{!hasTerminalContent ? (
				<div className="flex flex-1 items-center justify-center p-4">
					<div className="text-center">
						<TerminalIcon className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
						<p className="text-muted-foreground mb-2">Terminal</p>
						<p className="text-xs text-muted-foreground max-w-md">
							Execution logs will appear here when you run
							scripts, workflows, or data providers.
						</p>
					</div>
				</div>
			) : (
				<div
					ref={scrollRef}
					data-testid="terminal-log-viewport"
					onScroll={handleScroll}
					role="region"
					aria-label="Terminal log messages"
					tabIndex={0}
					className="min-h-0 min-w-0 flex-1 overflow-auto p-3 font-mono text-sm bg-muted/30 leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring @2xl:text-xs"
				>
					{/* Completed executions */}
					{terminalOutput?.executions.map((execution, execIndex) => {
						// Check if this is a Git operation (single log entry with source "git")
						const isGitOperation =
							execution.loggerOutput.length === 1 &&
							execution.loggerOutput[0]?.source === "git";

						return (
							<div key={execIndex}>
								{/* Separator for subsequent executions (skip for git operations) */}
								{execIndex > 0 && !isGitOperation && (
									<div className="border-t border-border/50 my-2" />
								)}

								{/* Logs with inline timestamps - no spacing between lines */}
								{execution.loggerOutput.map((log, logIndex) => (
									<TerminalLogRow key={logIndex} level={log.level} timestamp={formatTimestamp(log.timestamp || execution.timestamp)} message={log.message} color={getLogColor(log.level)} />
								))}

								{/* Error Display */}
								{execution.error && (
									<div className="whitespace-pre-wrap text-destructive [overflow-wrap:anywhere]">
										Error: {execution.error}
									</div>
								)}

								{/* Execution Result Display */}
								{execution.executionId && (
									<TerminalExecutionResult
										executionId={execution.executionId}
										status={execution.status}
									/>
								)}
							</div>
						);
					})}

					{/* Streaming logs - shown in real-time */}
					{streamingLogs.length > 0 && (
						<>
							{/* Separator between completed executions and streaming logs */}
							{terminalOutput &&
								terminalOutput.executions.length > 0 && (
									<div className="border-t border-border/50 my-2" />
								)}

							{streamingLogs.map((log, logIndex) => (
								<TerminalLogRow key={`streaming-${logIndex}`} level={log.level} timestamp={formatTimestamp(log.timestamp)} message={log.message} color={getLogColor(log.level)} />
							))}
						</>
					)}
				</div>
			)}
		</div>
	);
}


function TerminalLogRow({ level, timestamp, message, color }: { level: string; timestamp: string; message: string; color: string }) {
	return <div className={`grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 border-b border-border/40 py-3 last:border-0 @2xl:grid-cols-[auto_auto_minmax(0,1fr)] @2xl:py-1 ${color}`}>
		<span className="whitespace-nowrap text-xs text-muted-foreground tabular-nums">[{timestamp}]</span>
		<span className="text-xs font-medium [overflow-wrap:anywhere]">[{level.toUpperCase()}]</span>
		<TerminalLogMessage message={message} className="col-span-full min-w-0 whitespace-pre-wrap [overflow-wrap:anywhere] @2xl:col-span-1" />
	</div>;
}
