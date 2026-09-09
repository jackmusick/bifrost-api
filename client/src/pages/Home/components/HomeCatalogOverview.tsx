import { AppWindow, Bot, FileInput, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { HomeResource } from "@/services/home";
import { ResourceCard } from "./ResourceCard";

const categories = [
	{ kind: "app", label: "Apps", icon: AppWindow },
	{ kind: "form", label: "Forms", icon: FileInput },
	{ kind: "agent", label: "Agents", icon: Bot },
] as const;

/** A small type-grouped preview keeps the complete catalog discoverable without a wall of cards. */
export function HomeCatalogOverview({
	resources,
	onOpen,
	onPin,
	busy,
	onCategory,
	onViewAll,
}: {
	resources: HomeResource[];
	onOpen: (resource: HomeResource) => void;
	onPin: (resource: HomeResource) => void;
	busy: boolean;
	onCategory: (kind: string) => void;
	onViewAll: () => void;
}) {
	return (
		<section aria-label="Explore resources" className="space-y-4">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<h2 className="text-base font-semibold">
					Explore your workspace
				</h2>
				<Button variant="ghost" size="sm" onClick={onViewAll}>
					Browse all {resources.length}
					<ArrowRight className="size-4" />
				</Button>
			</div>
			<div className="grid gap-6 xl:grid-cols-3">
				{categories.map(({ kind, label, icon: Icon }) => {
					const items = resources.filter(
						(resource) => resource.kind === kind,
					);
					return (
						<section
							key={kind}
							aria-label={label}
							className="min-w-0 space-y-3"
						>
							<div className="flex items-center justify-between gap-2">
								<h3 className="flex items-center gap-2 text-sm font-semibold">
									<Icon className="size-4 text-muted-foreground" />
									{label}
									<span className="font-normal text-muted-foreground">
										{items.length}
									</span>
								</h3>
								{items.length > 0 && (
									<Button
										variant="ghost"
										size="sm"
										aria-label={`View all ${label.toLowerCase()}`}
										onClick={() => onCategory(kind)}
									>
										View all
									</Button>
								)}
							</div>
							{items.slice(0, 2).map((resource) => (
								<ResourceCard
									key={resource.key}
									resource={resource}
									onOpen={onOpen}
									onPin={onPin}
									busy={busy}
									compact
								/>
							))}
							{!items.length && (
								<p className="py-3 text-sm text-muted-foreground">
									No {label.toLowerCase()} available.
								</p>
							)}
						</section>
					);
				})}
			</div>
		</section>
	);
}
