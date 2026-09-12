import { Button } from "@/components/ui/button";

export function DocumentCollectionState({
	title,
	description,
	error = false,
	busy = false,
	action,
	onAction,
	headingLevel = 2,
}: {
	title: string;
	description?: string;
	error?: boolean;
	busy?: boolean;
	action?: string;
	onAction?: () => void;
	headingLevel?: 1 | 2;
}) {
	const Heading = headingLevel === 1 ? "h1" : "h2";
	return (
		<section className="shrink-0 space-y-3 p-[var(--bf-surface-pad)]">
			<div role={error ? "alert" : "status"}>
				<Heading
					className={
						headingLevel === 1
							? "font-display text-2xl font-semibold"
							: "font-medium"
					}
				>
					{title}
				</Heading>
				{description && (
					<p className="mt-1 text-sm text-muted-foreground">
						{description}
					</p>
				)}
			</div>
			{action && onAction && (
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					disabled={busy}
					onClick={onAction}
				>
					{busy ? "Retrying…" : action}
				</Button>
			)}
		</section>
	);
}
