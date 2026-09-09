import { Folder, Pencil, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getIcon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { HomeCollection } from "@/services/home";

export function CollectionStrip({
	collections,
	selected,
	onSelect,
	onEdit,
	onCreate,
}: {
	collections: HomeCollection[];
	selected: string | null;
	onSelect: (id: string | null) => void;
	onEdit: (collection: HomeCollection) => void;
	onCreate: () => void;
}) {
	return (
		<section className="space-y-3" aria-label="Collections">
			<div className="flex items-center justify-between gap-3">
				<h2 className="text-base font-semibold">Collections</h2>
				<Button variant="ghost" size="sm" onClick={onCreate}>
					<Plus className="size-4" />
					New collection
				</Button>
			</div>
			{collections.length === 0 ? (
				<div className="flex flex-wrap items-center justify-between gap-3 rounded border border-dashed p-4">
					<p className="max-w-xl text-sm text-muted-foreground">
						Keep related apps, forms, and agents together. Create a
						collection for a customer, team, or everyday task.
					</p>
					<Button variant="outline" onClick={onCreate}>
						Create a collection
					</Button>
				</div>
			) : (
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
					{collections.map((collection) => {
						const Icon = getIcon(collection.icon, Folder);
						return (
							<div
								key={collection.id}
								className={cn(
									"flex min-w-0 items-center gap-2 rounded-[var(--bf-radius-surface)] border bg-card px-3",
									selected === collection.id &&
										"border-primary bg-primary/5",
								)}
							>
								<button
									className="flex min-w-0 flex-1 items-center gap-3 py-3 text-left focus-visible:outline-ring"
									aria-pressed={selected === collection.id}
									onClick={() =>
										onSelect(
											selected === collection.id
												? null
												: collection.id,
										)
									}
								>
									<Icon className="size-5 shrink-0 text-primary" />
									<span className="min-w-0">
										<span className="block truncate text-sm font-medium">
											{collection.name}
										</span>
										<span className="mt-1 block truncate text-xs text-muted-foreground">
											{collection.shared
												? collection.organization_name ||
													"Shared across platform"
												: "Personal"}{" "}
											·{" "}
											{collection.resource_keys?.length ??
												0}{" "}
											items
										</span>
									</span>
								</button>
								{collection.can_edit && (
									<Button
										variant="ghost"
										size="icon"
										className="size-11 shrink-0"
										aria-label={`Edit ${collection.name}`}
										onClick={() => onEdit(collection)}
									>
										<Pencil className="size-4" />
									</Button>
								)}
							</div>
						);
					})}
				</div>
			)}
		</section>
	);
}
