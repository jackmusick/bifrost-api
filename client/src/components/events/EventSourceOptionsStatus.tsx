import { AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/** Shared feedback for option queries; never owns or clears the form draft. */
export function EventSourceOptionsStatus({
	label,
	pending,
	error,
	hasData,
	disabled,
	onRetry,
	hint,
	emptyMessage,
}: {
	label: string;
	pending?: boolean;
	error?: boolean;
	hasData: boolean;
	disabled?: boolean;
	onRetry: () => void;
	hint?: string;
	emptyMessage?: string;
}) {
	if (error)
		return (
			<Alert variant="destructive" className="min-w-0">
				<AlertCircle aria-hidden="true" className="size-4" />
				<AlertDescription className="min-w-0 space-y-3">
					<p className="[overflow-wrap:anywhere]">
						Could not {hasData ? "refresh" : "load"} {label}.{" "}
						{hasData
							? "Previously loaded options are still available."
							: hint || "Your entries have been kept."}
					</p>
					<Button
						type="button"
						variant="outline"
						className="h-auto min-h-11 max-w-full whitespace-normal px-3 py-2"
						disabled={pending || disabled}
						onClick={onRetry}
					>
						{pending ? `Retrying ${label}…` : `Retry ${label}`}
					</Button>
				</AlertDescription>
			</Alert>
		);
	if (pending && !hasData)
		return (
			<p
				role="status"
				className="flex items-center gap-2 text-sm text-muted-foreground"
			>
				<Loader2
					aria-hidden="true"
					className="size-4 shrink-0 motion-safe:animate-spin"
				/>
				Loading {label}…
			</p>
		);
	if (hasData && emptyMessage)
		return (
			<div className="space-y-2 text-sm text-muted-foreground">
				<p>{emptyMessage}</p>
				<Button
					type="button"
					variant="outline"
					className="h-auto min-h-11 max-w-full whitespace-normal px-3 py-2"
					disabled={pending || disabled}
					onClick={onRetry}
				>
					Refresh {label}
				</Button>
			</div>
		);
	return null;
}
