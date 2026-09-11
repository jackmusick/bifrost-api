import { useEffect, useState } from "react";
import { Clock, Radio, UserRound } from "lucide-react";
import { cn, formatRelativeTime, parseBackendDate } from "@/lib/utils";

interface ExecutionActivityTraceProps {
	status?: string;
	startedAt?: string | null;
	completedAt?: string | null;
	executedByName?: string | null;
	orgName?: string | null;
	isConnected?: boolean;
	isStreamingEnabled?: boolean;
	showProgressLine?: boolean;
	className?: string;
}

/** A compact, truthful run context strip. Only active work animates. */
export function ExecutionActivityTrace({
	status,
	startedAt,
	completedAt,
	executedByName,
	orgName,
	isConnected,
	isStreamingEnabled,
	showProgressLine = true,
	className,
}: ExecutionActivityTraceProps) {
	const active =
		status === "Running" || status === "Pending" || status === "Cancelling";
	const [now, setNow] = useState(Date.now);
	useEffect(() => {
		if (!active) return;
		const timer = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(timer);
	}, [active]);
	const started = startedAt ? parseBackendDate(startedAt).getTime() : NaN;
	const ended = completedAt ? parseBackendDate(completedAt).getTime() : now;
	const seconds = Math.max(0, Math.floor((ended - started) / 1000));
	const elapsed = Number.isFinite(seconds)
		? `${Math.floor(seconds / 60)
				.toString()
				.padStart(
					2,
					"0",
				)}:${(seconds % 60).toString().padStart(2, "0")}`
		: null;
	const connected = Boolean(isStreamingEnabled && isConnected);
	const connection = !isStreamingEnabled
		? "Connecting to live stream"
		: connected
			? "Live stream connected"
			: "Live stream reconnecting";
	return (
		<section
			aria-label="Execution activity"
			className={cn(
				"relative flex min-w-0 flex-wrap items-center gap-x-5 gap-y-2 border-b pb-3 text-xs text-muted-foreground",
				className,
			)}
		>
			<span className="flex min-w-0 items-center gap-2">
				<UserRound className="size-3.5 shrink-0" />
				<span className="[overflow-wrap:anywhere]">
					{executedByName || "Unknown"} · {orgName || "Global"}
				</span>
			</span>
			<span className="flex items-center gap-2">
				<Clock className="size-3.5 shrink-0" />
				{completedAt
					? `Completed ${formatRelativeTime(completedAt)}`
					: startedAt
						? `Started ${formatRelativeTime(startedAt)}`
						: status === "Scheduled"
							? "Scheduled"
							: "Not started"}
			</span>
			{elapsed && (
				<span
					className="font-mono tabular-nums"
					title="Total time since the run started"
				>
					Elapsed {elapsed}
				</span>
			)}
			{active && (
				<span className="flex items-center gap-2 sm:ml-auto">
					<Radio
						className={cn("size-3.5", connected && "text-primary")}
					/>
					{connection}
				</span>
			)}
			{active && showProgressLine && (
				<div
					aria-hidden="true"
					className="route-transition-progress-track absolute inset-x-0 bottom-0 h-0.5 overflow-hidden"
				>
					<div
						data-state="loading"
						className="route-transition-progress-fill h-full w-full shadow-none motion-reduce:animate-none"
					/>
				</div>
			)}
		</section>
	);
}
