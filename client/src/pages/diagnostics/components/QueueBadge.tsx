import { useId } from "react";
import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import type { QueueItem } from "@/services/workers";

interface QueueBadgeProps {
	items: QueueItem[];
	total?: number;
	isLoading?: boolean;
	error?: string;
	onRetry?: () => void;
	isRetrying?: boolean;
}

function formatRelativeTime(dateStr: string | null): string {
	if (!dateStr) return "Time unavailable";
	const timestamp = new Date(dateStr).getTime();
	if (!Number.isFinite(timestamp)) return "Time unavailable";
	const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
	if (seconds < 60) return `${seconds}s ago`;
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	return `${Math.floor(seconds / 3600)}h ago`;
}

/** Queue snapshot with touch and keyboard access to full execution identifiers. */
export function QueueBadge({
	items,
	total = items.length,
	isLoading,
	error,
	onRetry,
	isRetrying,
}: QueueBadgeProps) {
	const titleId = useId();
	return (
		<Popover>
			<PopoverTrigger asChild>
				<Button
					type="button"
					variant="outline"
					size="sm"
					className="min-h-11"
				>
					<Inbox className="size-4" aria-hidden="true" />
					{isLoading
						? "Loading queue…"
						: error
							? "Queue unavailable"
							: `${total} queued`}
				</Button>
			</PopoverTrigger>
			<PopoverContent
				align="start"
				aria-labelledby={titleId}
				className="w-96 max-w-[calc(100vw-2rem)]"
			>
				<h3 id={titleId} className="font-semibold">
					Execution queue
				</h3>
				{isLoading ? (
					<p role="status" className="text-muted-foreground">
						Loading queued executions…
					</p>
				) : error ? (
					<div className="space-y-3">
						<p
							role="alert"
							className="text-destructive [overflow-wrap:anywhere]"
						>
							{error}
						</p>
						{onRetry && (
							<Button
								type="button"
								variant="outline"
								className="min-h-11"
								disabled={isRetrying}
								onClick={onRetry}
							>
								{isRetrying ? "Retrying…" : "Retry queue"}
							</Button>
						)}
					</div>
				) : items.length === 0 ? (
					<p className="text-muted-foreground">
						{total === 0
							? "No jobs queued"
							: "Queue details are unavailable."}
					</p>
				) : (
					<>
						<p className="text-xs text-muted-foreground">
							{total} pending
							{total > items.length
								? ` · Showing the first ${items.length}`
								: ""}
						</p>
						<ol
							aria-label="Queued executions"
							className="max-h-72 overflow-y-auto divide-y"
						>
							{items.map((item) => (
								<li
									key={item.execution_id}
									className="space-y-2 py-3 first:pt-0 last:pb-0"
								>
									<div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
										<span>Position {item.position}</span>
										<span>
											{formatRelativeTime(item.queued_at)}
										</span>
									</div>
									<p className="font-mono text-xs [overflow-wrap:anywhere]">
										{item.execution_id}
									</p>
								</li>
							))}
						</ol>
					</>
				)}
			</PopoverContent>
		</Popover>
	);
}
