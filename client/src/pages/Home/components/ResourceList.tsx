import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResourceIcon } from "@/components/ResourceIcon";
import type { HomeResource } from "@/services/home";
import { resourceActions, resourceTypes } from "./ResourceCard";

export function ResourceList({
	resources,
	onOpen,
	onPin,
	busy,
}: {
	resources: HomeResource[];
	onOpen: (resource: HomeResource) => void;
	onPin: (resource: HomeResource) => void;
	busy?: boolean;
}) {
	return (
		<ul
			className="divide-y rounded-[var(--bf-radius-surface)] border bg-card"
			aria-label="Resources"
		>
			{resources.map((resource) => (
					<li
						key={resource.key}
						className="flex min-w-0 items-center gap-3 px-3 py-2 sm:px-4"
					>
						<ResourceIcon
							kind={resource.kind}
							id={resource.id}
							icon={resource.icon}
							logo={resource.logo_url ?? null}
							cacheKey={resource.logo_version ?? undefined}
							size="table"
						/>
						<button
							className="min-w-0 flex-1 py-1 text-left focus-visible:outline-ring"
							onClick={() => onOpen(resource)}
							disabled={busy}
						>
							<span className="block text-sm font-medium [overflow-wrap:anywhere]">
								{resource.name}
							</span>
							<span className="mt-1 block text-xs text-muted-foreground">
								{resource.organization_name} ·{" "}
								{resourceTypes[resource.kind]}
							</span>
							<span className="mt-1 hidden truncate text-xs text-muted-foreground xl:block">
								{resource.description}
							</span>
						</button>
						<Button
							variant="outline"
							className="hidden min-w-24 sm:inline-flex"
							disabled={busy}
							onClick={() => onOpen(resource)}
						>
							{resourceActions[resource.kind]}
						</Button>
						<Button
							variant="ghost"
							size="icon"
							className="size-11 shrink-0"
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
					</li>
				))}
		</ul>
	);
}
