/**
 * Card surfacing one flagged run on the agent detail Overview tab.
 *
 * Like RunCard but emphasises the verdict reason — used in a side column to
 * draw the user toward the runs that explicitly need their attention.
 */

import { ThumbsDown, ChevronRight, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { MarkdownContent } from "@/components/common/MarkdownContent";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils";
import type { components } from "@/lib/v1";

type AgentRun = components["schemas"]["AgentRunResponse"];

export interface NeedsReviewCardProps {
	run: AgentRun;
	onOpen?: () => void;
	className?: string;
}

export function NeedsReviewCard({
	run,
	onOpen,
	className,
}: NeedsReviewCardProps) {
	const startedAt = run.started_at ?? run.created_at;
	return (
		<div
			role={onOpen ? "button" : undefined}
			tabIndex={onOpen ? 0 : undefined}
			onClick={onOpen}
			onKeyDown={(e) => {
				if (onOpen && (e.key === "Enter" || e.key === " ")) {
					e.preventDefault();
					onOpen();
				}
			}}
			className={cn(
				"flex min-h-14 items-start gap-3 rounded-[var(--bf-radius-feature)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-4 shadow-sm transition-colors motion-reduce:transition-none",
				onOpen &&
					"cursor-pointer hover:bg-[var(--bf-danger-soft)]/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
				className,
			)}
			data-slot="needs-review-card"
		>
			<div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]">
				<ThumbsDown size={16} />
			</div>
			<div className="flex min-w-0 flex-1 flex-col gap-1">
				<div className="flex items-center gap-2">
					<Badge
						variant="destructive"
						className="bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
					>
						Flagged
					</Badge>
					<div className="min-w-0 flex-1 break-words text-sm font-medium leading-6">
						{run.asked ? (
							<MarkdownContent
								content={run.asked}
								variant="preview"
							/>
						) : (
							<span className="text-muted-foreground">—</span>
						)}
					</div>
				</div>
				{run.verdict_note ? (
					<div
						className="break-words text-sm leading-6 text-muted-foreground"
						title={run.verdict_note}
					>
						“{run.verdict_note}”
					</div>
				) : run.did ? (
					<div className="break-words text-sm leading-6 text-muted-foreground">
						<MarkdownContent content={run.did} variant="preview" />
					</div>
				) : null}
				<div className="flex items-center gap-1 text-[11px] text-muted-foreground">
					<Clock size={11} />
					{formatRelativeTime(startedAt)}
				</div>
			</div>
			{onOpen ? (
				<ChevronRight
					size={14}
					className="mt-1 shrink-0 text-muted-foreground"
				/>
			) : null}
		</div>
	);
}
