import { useEffect, useRef } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function SecurityFeedback({
	message,
	retryLabel,
	onRetry,
	pending = false,
	focus = false,
}: {
	message: string;
	retryLabel?: string;
	onRetry?: () => void;
	pending?: boolean;
	focus?: boolean;
}) {
	const ref = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (focus) {
			ref.current?.focus();
			ref.current?.scrollIntoView?.({ block: "nearest" });
		}
	}, [focus, message]);
	return (
		<Alert ref={ref} tabIndex={-1} variant="destructive">
			<AlertDescription className="space-y-3">
				<p>{message}</p>
				{onRetry && (
					<Button
						type="button"
						variant="outline"
						disabled={pending}
						className="min-h-11"
						onClick={onRetry}
					>
						{pending ? "Retrying…" : (retryLabel ?? "Retry")}
					</Button>
				)}
			</AlertDescription>
		</Alert>
	);
}
