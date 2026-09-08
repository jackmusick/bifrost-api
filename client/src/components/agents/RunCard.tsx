/**
 * Compact card for one agent run, used in the agent detail Runs tab.
 *
 * Shows: status indicator, asked text, did/error text, verdict badge,
 * timing metadata (when, duration, tokens), and inline verdict toggles.
 *
 * Adapted from the mockup's `RunCard` (AgentDetailPage.tsx) — replaces inline
 * styles with Tailwind + shadcn primitives.
 */

import { ThumbsDown, ThumbsUp } from "lucide-react";
import type { MouseEvent, ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/v1";

import type { Verdict } from "./RunReviewPanel";
import { RunSummaryContent } from "./RunSummaryContent";

type AgentRun = components["schemas"]["AgentRunResponse"];

export interface RunCardProps {
	run: AgentRun;
	verdict?: Verdict;
	highlight?: string;
	onOpen?: () => void;
	onVerdict?: (v: Verdict) => void;
	/** Called when the inline "what should it have done" note is saved.
	 *  Only surfaces while verdict === "down" and this callback is provided. */
	onNote?: (runId: string, note: string) => void;
	conversationCount?: number;
	reviewDisabled?: boolean;
	reviewFeedback?: ReactNode;
}

export function RunCard({
	run,
	verdict = null,
	highlight,
	onOpen,
	onVerdict,
	onNote,
	conversationCount = 0,
	reviewDisabled = false,
	reviewFeedback,
}: RunCardProps) {
	const canVerdict = run.status === "completed";

	function handleVerdict(target: Verdict, e: MouseEvent) {
		e.stopPropagation();
		if (!onVerdict || reviewDisabled) return;
		onVerdict(verdict === target ? null : target);
	}

	const showNoteInput = verdict === "down" && onNote;
	return (
		<div
			className={cn(
				"min-w-0 rounded-[var(--bf-radius-surface)] border border-border bg-card",
				onOpen && "hover:bg-accent/50",
			)}
			data-slot="run-card"
		>
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
					"flex min-w-0 items-start gap-3 p-4 rounded-[var(--bf-radius-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
					onOpen && "cursor-pointer",
				)}
			>
				<RunSummaryContent
					run={run}
					highlight={highlight}
					titleTrailing={
						verdict === "up" ? (
							<span className="inline-flex items-center gap-1 rounded border border-[var(--bf-success)]/30 bg-[var(--bf-success-soft)] px-1.5 py-0.5 text-xs font-medium text-[var(--bf-success)]">
								<ThumbsUp size={11} /> Good
							</span>
						) : verdict === "down" ? (
							<span className="inline-flex items-center gap-1 rounded border border-[var(--bf-danger)]/30 bg-[var(--bf-danger-soft)] px-1.5 py-0.5 text-xs font-medium text-[var(--bf-danger)]">
								<ThumbsDown size={11} /> Wrong
								{conversationCount > 0
									? ` · ${conversationCount} msg`
									: ""}
							</span>
						) : null
					}
				/>
			</div>
			<div
				className="flex min-w-0 items-center justify-end border-t px-4 py-3"
				onClick={(e) => e.stopPropagation()}
			>
				{canVerdict && onVerdict ? (
					<div className="flex gap-1">
						<button
							type="button"
							disabled={reviewDisabled}
							aria-label="Mark as good"
							aria-pressed={verdict === "up"}
							title="Good"
							onClick={(e) => handleVerdict("up", e)}
							className={cn(
								"grid size-11 place-items-center rounded-[var(--bf-radius-control)] border disabled:cursor-not-allowed disabled:opacity-50 motion-safe:transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
								verdict === "up"
									? "border-[var(--bf-success)] bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
									: "bg-background hover:bg-accent",
							)}
						>
							<ThumbsUp size={14} />
						</button>
						<button
							type="button"
							disabled={reviewDisabled}
							aria-label="Mark as wrong"
							aria-pressed={verdict === "down"}
							title="Wrong"
							onClick={(e) => handleVerdict("down", e)}
							className={cn(
								"grid size-11 place-items-center rounded-[var(--bf-radius-control)] border disabled:cursor-not-allowed disabled:opacity-50 motion-safe:transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
								verdict === "down"
									? "border-[var(--bf-danger)] bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
									: "bg-background hover:bg-accent",
							)}
						>
							<ThumbsDown size={14} />
						</button>
					</div>
				) : (
					<span className="text-xs text-muted-foreground">n/a</span>
				)}
			</div>
			{reviewFeedback ? (
				<div className="border-t p-4">{reviewFeedback}</div>
			) : null}
			{showNoteInput ? (
				<div className="border-t p-4">
					<Input
						type="text"
						disabled={reviewDisabled}
						aria-label="What should it have done?"
						placeholder="What should it have done?"
						defaultValue={run.verdict_note ?? ""}
						onClick={(e) => e.stopPropagation()}
						onKeyDown={(e) => {
							e.stopPropagation();
							if (e.key === "Enter") {
								(e.currentTarget as HTMLInputElement).blur();
							}
						}}
						onBlur={(e) => {
							const next = e.currentTarget.value.trim();
							const prev = run.verdict_note ?? "";
							if (!reviewDisabled && next !== prev)
								onNote?.(run.id, next);
						}}
						className="min-h-11 text-sm"
						data-testid="run-card-note-input"
					/>
				</div>
			) : null}
		</div>
	);
}
