import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";

export function RunActionFeedback({
	pending,
	failed,
	onRetry,
	message = "Could not save your review. Your note is still here.",
	pendingLabel = "Saving review…",
	retryLabel = "Retry review",
}: {
	pending: boolean;
	failed: boolean;
	onRetry: () => void;
	message?: string;
	pendingLabel?: string;
	retryLabel?: string;
}) {
	const ref = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (failed) {
			ref.current?.focus();
			ref.current?.scrollIntoView?.({ block: "nearest" });
		}
	}, [failed]);
	if (pending)
		return (
			<p role="status" className="text-sm text-muted-foreground">
				{pendingLabel}
			</p>
		);
	if (!failed) return null;
	return (
		<div
			ref={ref}
			tabIndex={-1}
			role="alert"
			className="space-y-3 rounded-[var(--bf-radius-surface)] border bg-[var(--bf-warning-soft)] p-4 text-sm"
		>
			<p>{message}</p>
			<Button
				type="button"
				variant="outline"
				className="min-h-11"
				onClick={onRetry}
			>
				{retryLabel}
			</Button>
		</div>
	);
}
