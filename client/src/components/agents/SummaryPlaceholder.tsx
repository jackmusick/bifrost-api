/**
 * Muted placeholder shown when a run's asked/did fields are empty.
 *
 * Keyed off BOTH the run's overall `status` and its `summary_status`:
 *   - A run that never reached `status='completed'` can't be summarized (the
 *     summarizer's idempotent guard short-circuits silently), so showing
 *     "Summary pending…" would be a lie. Surface the real lifecycle state
 *     instead.
 *   - Only when the run is genuinely completed does summary_status matter.
 *
 * Never falls back to raw run.input / run.output — those are opaque (often
 * HTML email bodies) and make the UI unreadable.
 */

import {
	AlertTriangle,
	CheckCircle2,
	Clock3,
	CircleX,
	Loader2,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface SummaryPlaceholderProps {
	/** The run's summary_status (pending/generating/completed/failed). */
	status: string | undefined | null;
	/** The run's overall status (queued/running/completed/failed/...). Optional
	 *  for backwards compat, but preferred — lets us tell users when a run
	 *  never actually finished. */
	runStatus?: string | undefined | null;
	muted?: boolean;
	className?: string;
}

type SummaryTone = "neutral" | "info" | "success" | "warning" | "danger";

interface SummaryMeta {
	text: string;
	ariaLabel: string;
	tone: SummaryTone;
	icon?: React.ReactNode;
	loading?: boolean;
}

export function SummaryPlaceholder({
	status,
	runStatus,
	muted = false,
	className,
}: SummaryPlaceholderProps) {
	const summary = resolveSummary(status, runStatus);

	return (
		<span
			className={cn(
				"inline-flex items-center gap-1.5 rounded-[var(--bf-radius-control)] border px-2 py-0.5 text-xs font-medium leading-5",
				toneClasses(summary.tone),
				muted && "opacity-80",
				className,
			)}
			role="status"
			aria-live="polite"
			aria-label={summary.ariaLabel}
			data-status={status ?? undefined}
			data-run-status={runStatus ?? undefined}
		>
			{summary.icon ? (
				<span
					aria-hidden="true"
					className={cn(
						"inline-flex items-center justify-center",
						summary.loading && "animate-spin motion-reduce:animate-none",
					)}
				>
					{summary.icon}
				</span>
			) : null}
			<span aria-hidden="true" className="whitespace-nowrap">
				{summary.text}
			</span>
		</span>
	);
}

function resolveSummary(
	status: string | undefined | null,
	runStatus: string | undefined | null,
): SummaryMeta {
	if (runStatus === "running" || runStatus === "queued") {
		return {
			text: "Run in progress…",
			ariaLabel: "Run in progress",
			tone: "info",
			icon: <Loader2 size={11} />,
			loading: true,
		};
	}

	if (runStatus === "failed") {
		return {
			text: "Run failed",
			ariaLabel: "Run failed",
			tone: "danger",
			icon: <CircleX size={11} />,
		};
	}

	if (runStatus === "budget_exceeded") {
		return {
			text: "Budget exceeded",
			ariaLabel: "Budget exceeded",
			tone: "warning",
			icon: <AlertTriangle size={11} />,
		};
	}

	if (runStatus === "cancelled") {
		return {
			text: "Run cancelled",
			ariaLabel: "Run cancelled",
			tone: "neutral",
			icon: <Clock3 size={11} />,
		};
	}

	if (status === "failed") {
		return {
			text: "Summary failed",
			ariaLabel: "Summary failed",
			tone: "danger",
			icon: <AlertTriangle size={11} />,
		};
	}

	if (status === "generating") {
		return {
			text: "Summarizing…",
			ariaLabel: "Summarizing",
			tone: "info",
			icon: <Loader2 size={11} />,
			loading: true,
		};
	}

	if (status === "completed") {
		return {
			text: "—",
			ariaLabel: "Summary completed",
			tone: "success",
			icon: <CheckCircle2 size={11} />,
		};
	}

	return {
		text: "Summary pending…",
		ariaLabel: "Summary pending",
		tone: "neutral",
		icon: <Clock3 size={11} />,
	};
}

function toneClasses(tone: SummaryTone) {
	switch (tone) {
		case "info":
			return "border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)] text-[var(--bf-info)]";
		case "success":
			return "border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]";
		case "warning":
			return "border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]";
		case "danger":
			return "border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]";
		case "neutral":
		default:
			return "border-border bg-muted/40 text-muted-foreground";
	}
}
