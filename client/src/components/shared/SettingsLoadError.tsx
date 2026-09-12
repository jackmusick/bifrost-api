import { Button } from "@/components/ui/button";
export function SettingsLoadError({
	name,
	onRetry,
}: {
	name: string;
	onRetry: () => void;
}) {
	return (
		<div
			role="alert"
			className="space-y-3 rounded-[var(--bf-radius-surface)] border border-destructive/30 p-[var(--bf-surface-pad)]"
		>
			<p className="text-sm">
				Couldn't load {name}. Retry before making changes.
			</p>
			<Button
				type="button"
				variant="outline"
				className="min-h-11"
				onClick={onRetry}
			>
				Retry
			</Button>
		</div>
	);
}
