import { useEffect, useRef, useState } from "react";
import { Activity, ArrowDown, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExecutionLogEntry } from "@/lib/executionLogs";

/** A readable stream of actual workflow messages; technical fields stay in Logs. */
export function ExecutionActivityFeed({
	logs,
	onViewLogs,
	active = true,
}: {
	logs: ExecutionLogEntry[];
	active?: boolean;
	onViewLogs: () => void;
}) {
	const [initialCount] = useState(logs.length);
	const viewport = useRef<HTMLDivElement>(null);
	const following = useRef(true);
	const [paused, setPaused] = useState(false);
	useEffect(() => {
		if (following.current && viewport.current)
			viewport.current.scrollTop = viewport.current.scrollHeight;
	}, [logs]);
	if (!logs.length) return null;
	return (
		<section
			className={
				active ? "min-w-0" : "min-w-0 border-t border-border pt-5"
			}
			aria-label="Run Activity"
		>
			<div className="mb-4 flex items-center justify-between gap-3">
				<div className="flex min-w-0 items-center gap-3">
					<Activity
						className="size-5 shrink-0 text-primary"
						aria-hidden="true"
					/>
					<div className="min-w-0">
						<h3 className="font-display text-lg font-semibold leading-tight">
							Run Activity
						</h3>
						<p className="mt-1 text-xs tabular-nums text-muted-foreground">
							{logs.length}{" "}
							{logs.length === 1 ? "message" : "messages"}
							{active
								? " · Run in progress"
								: " · Recorded during this run"}
						</p>
					</div>
				</div>
				<Button
					type="button"
					variant="ghost"
					size="sm"
					className="shrink-0 px-2 text-xs"
					onClick={onViewLogs}
				>
					Open logs
				</Button>
			</div>
			<div
				ref={viewport}
				role="log"
				aria-label="Workflow messages"
				aria-live="off"
				tabIndex={0}
				className="max-h-80 overflow-y-auto overscroll-contain rounded-[var(--bf-radius-surface)] border border-border bg-muted/30 px-2 focus-visible:outline-ring sm:px-3"
				onScroll={(event) => {
					const element = event.currentTarget;
					following.current =
						element.scrollHeight -
							element.scrollTop -
							element.clientHeight <
						32;
					setPaused(!following.current);
				}}
			>
				<ol className="space-y-0">
					{logs.map((log, index) => {
						const warning = /warn|error|critical/i.test(
							log.level ?? "",
						);
						return (
							<li
								key={log.sequence ?? log.id ?? index}
								className="execution-live-row grid gap-1 px-2 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-3"
								data-arriving={
									active && index >= initialCount
										? "true"
										: undefined
								}
								data-latest={
									active && index === logs.length - 1
										? "true"
										: undefined
								}
								data-warning={warning ? "true" : undefined}
							>
								<p className="min-w-0 flex-1 whitespace-pre-wrap leading-relaxed [overflow-wrap:anywhere]">
									{warning && (
										<AlertTriangle
											aria-label={log.level}
											className="mr-1.5 inline size-3.5 align-[-0.125em] text-warning"
										/>
									)}
									{log.message}
								</p>
								{log.timestamp && (
									<time
										dateTime={log.timestamp}
										className="text-xs tabular-nums text-muted-foreground sm:pt-1"
									>
										{formatActivityTime(log.timestamp)}
									</time>
								)}
								{log.data &&
									Object.keys(log.data).length > 0 && (
										<details className="min-w-0 sm:col-span-2">
											<summary className="cursor-pointer text-xs text-muted-foreground">
												Message details
											</summary>
											<pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs [overflow-wrap:anywhere]">
												{JSON.stringify(
													log.data,
													null,
													2,
												)}
											</pre>
										</details>
									)}
							</li>
						);
					})}
				</ol>
			</div>
			{paused && (
				<Button
					type="button"
					variant="outline"
					size="sm"
					className="mt-3"
					onClick={() => {
						following.current = true;
						setPaused(false);
						if (viewport.current)
							viewport.current.scrollTop =
								viewport.current.scrollHeight;
					}}
				>
					<ArrowDown className="size-4" />
					Follow latest activity
				</Button>
			)}
		</section>
	);
}

function formatActivityTime(timestamp: string): string {
	const date = new Date(timestamp);
	if (Number.isNaN(date.getTime())) return timestamp;
	return date.toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
	});
}
