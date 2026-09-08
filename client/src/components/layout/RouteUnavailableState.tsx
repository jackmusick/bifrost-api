import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

/** Host-owned unavailable states share one responsive composition. */
export function RouteUnavailableState({
	title,
	description,
	children,
}: {
	title: string;
	description: ReactNode;
	children?: ReactNode;
}) {
	return (
		<div className="flex min-h-dvh items-center justify-center bg-background p-4 sm:p-6">
			<section className="w-full max-w-lg space-y-6 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]">
				<div className="space-y-3">
					<AlertTriangle
						aria-hidden="true"
						className="size-6 text-muted-foreground"
					/>
					<h1 className="font-display text-2xl font-semibold tracking-tight [overflow-wrap:anywhere]">
						{title}
					</h1>
					<div className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
						{description}
					</div>
				</div>
				{children && (
					<div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
						{children}
					</div>
				)}
			</section>
		</div>
	);
}
