import type { ReactNode } from "react";

export function ConfigurationOverrideRecord({
	organization,
	configKey,
	type,
	children,
	actions,
}: {
	organization: string;
	configKey: string;
	type: string;
	children: ReactNode;
	actions: ReactNode;
}) {
	return (
		<li className="min-w-0 space-y-3 py-5 first:pt-0 last:pb-0">
			<div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
				<div className="min-w-0 space-y-1 [overflow-wrap:anywhere]">
					<h3 className="font-medium">{organization}</h3>
					<p className="text-sm">
						<code>{configKey}</code>{" "}
						<span className="text-muted-foreground">({type})</span>
					</p>
				</div>
				{actions}
			</div>
			<div className="min-w-0">{children}</div>
		</li>
	);
}
