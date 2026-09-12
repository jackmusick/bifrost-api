import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { RefreshCw, Clock, Inbox } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { QueueItem } from "@/services/workers";

interface QueueSectionProps {
	items: QueueItem[];
	isLoading?: boolean;
	onRefresh?: () => void;
}

/**
 * Format relative time from ISO date string
 */
function formatRelativeTime(dateStr: string | null | undefined): string {
	if (!dateStr) return "Unknown";
	const date = new Date(dateStr);
	if (Number.isNaN(date.getTime())) return "Unknown";
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffSec = Math.max(0, Math.floor(diffMs / 1000));

	if (diffSec < 60) return `${diffSec}s ago`;
	const minutes = Math.floor(diffSec / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	return `${hours}h ago`;
}

export function QueueSection({
	items,
	isLoading,
	onRefresh,
}: QueueSectionProps) {
	const reduceMotion = useReducedMotion();
	return (
		<Card>
			<CardHeader className="pb-3">
				<div className="flex flex-wrap items-center justify-between gap-3">
					<div className="flex min-w-0 flex-wrap items-center gap-2">
						<CardTitle className="text-lg">Queue</CardTitle>
						<Badge variant="secondary">
							{items.length} pending
						</Badge>
					</div>
					{onRefresh && (
						<Button
							variant="ghost"
							size="icon"
							className="size-11 shrink-0"
							aria-label="Refresh queue"
							onClick={onRefresh}
							disabled={isLoading}
						>
							<RefreshCw
								className={`h-4 w-4 ${isLoading ? "motion-safe:animate-spin" : ""}`}
							/>
						</Button>
					)}
				</div>
			</CardHeader>
			<CardContent>
				{isLoading && items.length === 0 ? (
					<p
						role="status"
						className="py-8 text-center text-sm text-muted-foreground"
					>
						Loading queued jobs…
					</p>
				) : items.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
						<Inbox className="h-8 w-8 mb-2" />
						<p className="text-sm">No jobs queued</p>
					</div>
				) : (
					<div className="divide-y">
						<AnimatePresence mode="popLayout">
							{items.map((item) => (
								<motion.div
									key={item.execution_id}
									initial={
										reduceMotion
											? false
											: { opacity: 0, y: -10 }
									}
									animate={{ opacity: 1, y: 0 }}
									exit={
										reduceMotion
											? undefined
											: { opacity: 0, x: 20 }
									}
									transition={{
										duration: reduceMotion ? 0 : 0.2,
									}}
									layout={!reduceMotion}
									className="flex min-w-0 flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
								>
									<div className="flex min-w-0 items-start gap-3">
										<span className="text-muted-foreground font-mono text-sm shrink-0">
											#{item.position}
										</span>
										<span className="min-w-0 font-mono text-sm [overflow-wrap:anywhere]">
											{item.execution_id}
										</span>
									</div>
									<div className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
										<Clock className="h-3 w-3" />
										<span>
											queued{" "}
											{formatRelativeTime(item.queued_at)}
										</span>
									</div>
								</motion.div>
							))}
						</AnimatePresence>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
