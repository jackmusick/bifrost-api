import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

/** Shared hierarchy for execution sections in full-page and drawer layouts. */
export function ExecutionSectionHeading({
	title,
	icon: Icon,
	description,
	action,
}: {
	title: string;
	icon: LucideIcon;
	description?: ReactNode;
	action?: ReactNode;
}) {
	return (
		<div className="mb-4 flex items-start justify-between gap-3">
			<div className="flex min-w-0 items-start gap-3">
				<Icon
					className="mt-0.5 size-5 shrink-0 text-primary"
					aria-hidden="true"
				/>
				<div className="min-w-0">
					<h3 className="font-display text-lg font-semibold leading-tight text-foreground">
						{title}
					</h3>
					{description && (
						<p className="mt-1 text-xs leading-relaxed text-muted-foreground">
							{description}
						</p>
					)}
				</div>
			</div>
			{action && <div className="shrink-0">{action}</div>}
		</div>
	);
}
