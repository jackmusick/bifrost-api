import { Button } from "@/components/ui/button";

interface UserLookupNoticeProps {
	resource: string;
	loading: boolean;
	failed: boolean;
	retrying?: boolean;
	onRetry: () => void;
}

export function UserLookupNotice({
	resource,
	loading,
	failed,
	retrying,
	onRetry,
}: UserLookupNoticeProps) {
	if (failed)
		return (
			<div
				role="alert"
				className="space-y-2 rounded-[var(--bf-radius-surface)] border border-destructive/30 p-3 text-sm"
			>
				<p>
					Could not load {resource}. Retry to choose from the
					available options.
				</p>
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					disabled={retrying}
					onClick={onRetry}
				>
					Retry {resource}
				</Button>
			</div>
		);
	return loading ? (
		<p role="status" className="sr-only">
			Loading {resource}…
		</p>
	) : null;
}
