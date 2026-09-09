import { useEffect, useRef, useState } from "react";
import { ArrowDown, AlertTriangle, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExecutionLogEntry } from "@/lib/executionLogs";

/** A readable stream of actual workflow messages; technical fields stay in Logs. */
export function ExecutionActivityFeed({
	logs,
	onViewLogs,
}: {
	logs: ExecutionLogEntry[];
	onViewLogs: () => void;
}) {
	const viewport = useRef<HTMLDivElement>(null);
	const following = useRef(true);
	const [paused, setPaused] = useState(false);
	useEffect(() => {
		if (following.current && viewport.current)
			viewport.current.scrollTop = viewport.current.scrollHeight;
	}, [logs]);
	if (!logs.length) return null;
	return (
		<section className="min-w-0" aria-label="Live activity">
			<div className="mb-2 flex items-center justify-between gap-3">
				<h3 className="text-sm font-semibold">Activity</h3>
				<Button
					type="button"
					variant="ghost"
					size="sm"
					onClick={onViewLogs}
				>
					View logs
				</Button>
			</div>
			<div
				ref={viewport}
				role="log"
				aria-label="Workflow messages"
				aria-live="off"
				tabIndex={0}
				className="max-h-80 overflow-y-auto overscroll-contain pr-3 focus-visible:outline-ring"
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
								className="relative flex gap-3 py-2.5 text-sm"
							>
								<span className="relative flex w-4 shrink-0 justify-center">
									{index < logs.length - 1 && (
										<span
											aria-hidden="true"
											className="absolute bottom-[-0.625rem] top-5 w-px bg-border"
										/>
									)}
									{warning ? (
										<AlertTriangle
											aria-label={log.level}
											className="mt-0.5 size-4 text-warning"
										/>
									) : (
										<Circle
											aria-hidden="true"
											className="mt-1 size-2 fill-primary/30 text-primary/60"
										/>
									)}
								</span>
								<p className="min-w-0 flex-1 whitespace-pre-wrap leading-relaxed [overflow-wrap:anywhere]">
									{log.message}
								</p>
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
