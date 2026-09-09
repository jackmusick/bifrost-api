import { createElement } from "react";
import { ArrowRight, Building2, Star } from "lucide-react";
import { getIcon } from "@/lib/icons";
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
}: {
	resource: HomeResource;
	onOpen: (resource: HomeResource) => void;
	onPin: (resource: HomeResource) => void;
	busy?: boolean;
}) {
	const Icon = getIcon(resource.icon);
	return (
		<article className="flex min-w-0 flex-col rounded-[var(--bf-radius-surface)] border bg-card">
			<div className="flex items-start gap-3 p-3 sm:p-4 sm:pb-2">
				<div className="flex size-10 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] bg-primary/10 text-primary">
					{createElement(Icon, { className: "size-5" })}
				</div>
				<div className="min-w-0 flex-1">
					<button
						className="text-left text-sm font-semibold hover:underline focus-visible:outline-ring [overflow-wrap:anywhere]"
						onClick={() => onOpen(resource)}
						disabled={busy}
					>
						{resource.name}
					</button>
					<p className="mt-1 text-xs text-muted-foreground">
						{resourceTypes[resource.kind]}
						<span className="sm:hidden">
							{" "}
							· {resource.organization_name}
						</span>
					</p>
				</div>
				<Button
					variant="ghost"
					size="icon"
					className="-mr-2 -mt-2 size-11 shrink-0"
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
			<p className="hidden min-h-10 sm:line-clamp-2 px-4 text-sm leading-5 text-muted-foreground">
				{resource.description || resourceActions[resource.kind]}
			</p>
			<p className="mt-auto hidden items-center sm:flex gap-2 px-4 py-3 text-xs text-muted-foreground">
				<Building2 className="size-3.5 shrink-0" />
				<span className="truncate">{resource.organization_name}</span>
			</p>
			<Button
				variant="ghost"
				disabled={busy}
				className="hidden h-11 justify-between sm:flex rounded-none border-t px-4 text-primary"
				onClick={() => onOpen(resource)}
			>
				{resourceActions[resource.kind]}
				<ArrowRight className="size-4" />
			</Button>
		</article>
	);
}
