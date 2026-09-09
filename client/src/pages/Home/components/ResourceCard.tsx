import { Building2, Star } from "lucide-react";
import { ResourceIcon } from "@/components/ResourceIcon";
import { Button } from "@/components/ui/button";
import type { HomeResource } from "@/services/home";

export const resourceActions = {
	app: "Open app",
	form: "Start form",
	agent: "Chat",
};
export const resourceTypes = { app: "App", form: "Form", agent: "Agent" };

export function ResourceCard({
	resource,
	onOpen,
	onPin,
	busy,
	compact = false,
}: {
	resource: HomeResource;
	onOpen: (resource: HomeResource) => void;
	onPin: (resource: HomeResource) => void;
	busy?: boolean;
	compact?: boolean;
}) {
	return (
		<article className="relative flex min-w-0 flex-col rounded-[var(--bf-radius-surface)] border bg-card transition-colors hover:border-primary/40 focus-within:border-primary">
			<div className="flex items-start gap-3 p-3 sm:p-4 sm:pb-2">
				<ResourceIcon
					kind={resource.kind}
					id={resource.id}
					icon={resource.icon}
					logo={resource.logo_url ?? null}
					cacheKey={resource.logo_version ?? undefined}
					size="card"
				/>
				<div className="min-w-0 flex-1">
					<button
						className="text-left text-sm font-semibold after:absolute after:inset-0 after:rounded-[var(--bf-radius-surface)] focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-ring [overflow-wrap:anywhere]"
						onClick={() => onOpen(resource)}
						disabled={busy}
					>
						{resource.name}
					</button>
					<p className="mt-1 text-xs text-muted-foreground">
						{resourceTypes[resource.kind]}
						<span className={compact ? "" : "sm:hidden"}>
							{" "}
							· {resource.organization_name}
						</span>
					</p>
				</div>
				<Button
					variant="ghost"
					size="icon"
					className="relative z-10 -mr-2 -mt-2 size-11 shrink-0"
					aria-label={`${resource.pinned ? "Unpin" : "Pin"} ${resource.name}`}
					aria-pressed={resource.pinned}
					disabled={busy}
					onClick={() => onPin(resource)}
				>
					<Star
						className={
							resource.pinned
								? "size-4 fill-primary text-primary"
								: "size-4"
						}
					/>
				</Button>
			</div>
			{!compact && (
				<>
					<p className="hidden min-h-10 sm:line-clamp-2 px-4 text-sm leading-5 text-muted-foreground">
						{resource.description || resourceActions[resource.kind]}
					</p>
					<p className="mt-auto hidden items-center sm:flex gap-2 px-4 py-3 text-xs text-muted-foreground">
						<Building2 className="size-3.5 shrink-0" />
						<span className="truncate">
							{resource.organization_name}
						</span>
					</p>
				</>
			)}
		</article>
	);
}
