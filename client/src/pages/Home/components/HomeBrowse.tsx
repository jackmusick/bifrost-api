import type { ReactNode } from "react";
import { LayoutGrid, List, X, Pencil } from "lucide-react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

import { ListPagination } from "@/components/pagination/ListPagination";
import type { HomeCollection, HomeResource } from "@/services/home";
import { ResourceCard } from "./ResourceCard";
import { ResourceList } from "./ResourceList";
export function HomeBrowse({
	filters,
	selected,
	onEdit,
	total,
	grid,
	sort,
	visible,
	resourceCount,
	busy,
	page,
	updateParam,
	onOpen,
	onPin,
	onPageChange,
}: {
	filters?: ReactNode;
	selected?: HomeCollection;
	onEdit: (collection: HomeCollection) => void;
	total: number;
	grid: boolean;
	sort: string;
	visible: HomeResource[];
	resourceCount: number;
	busy: boolean;
	page: number;
	updateParam: (key: string, value: string | null) => void;
	onOpen: (resource: HomeResource) => void;
	onPin: (resource: HomeResource) => void;
	onPageChange: (offset: number) => void;
}) {
	return (
		<section className="space-y-3" aria-label="Browse resources">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex min-w-0 flex-wrap items-center gap-2">
					{filters}
					<h2
						className={
							selected
								? "text-base font-semibold [overflow-wrap:anywhere]"
								: "sr-only"
						}
					>
						{selected?.name ?? "Resources"}
					</h2>
					<span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">
						{total} resources
					</span>
					{selected?.can_edit && (
						<Button
							size="icon"
							variant="ghost"
							aria-label={`Edit ${selected.name}`}
							onClick={() => onEdit(selected)}
						>
							<Pencil className="size-4" />
						</Button>
					)}
					{selected && (
						<Button
							size="icon"
							variant="ghost"
							aria-label="Clear collection filter"
							onClick={() => updateParam("collection", null)}
						>
							<X className="size-4" />
						</Button>
					)}
				</div>
				<div className="flex max-w-full flex-wrap items-center gap-1">
					<Select
						value={sort}
						onValueChange={(value) => updateParam("sort", value)}
					>
						<SelectTrigger
							aria-label="Sort resources"
							className="mr-2 w-40"
						>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{selected && (
								<SelectItem value="collection">
									Collection order
								</SelectItem>
							)}
							<SelectItem value="recommended">
								Recommended
							</SelectItem>
							<SelectItem value="name">Name</SelectItem>
							<SelectItem value="recent">
								Recently opened
							</SelectItem>
						</SelectContent>
					</Select>
					<Button
						size="icon"
						variant={grid ? "ghost" : "secondary"}
						aria-label="List view"
						aria-pressed={!grid}
						onClick={() => updateParam("view", "list")}
					>
						<List className="size-4" />
					</Button>
					<Button
						size="icon"
						variant={grid ? "secondary" : "ghost"}
						aria-label="Card view"
						aria-pressed={grid}
						onClick={() => updateParam("view", "grid")}
					>
						<LayoutGrid className="size-4" />
					</Button>
				</div>
			</div>
			{selected?.description && (
				<p className="text-sm text-muted-foreground">
					{selected.description}
				</p>
			)}
			{visible.length === 0 ? (
				<p className="rounded border border-dashed p-6 text-sm text-muted-foreground">
					{resourceCount
						? "No resources match these filters. Try another search or collection."
						: "No launchable resources are available yet. Published apps, active forms, and chat agents will appear here when you have access."}
				</p>
			) : grid ? (
				<div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
					{visible.map((resource) => (
						<ResourceCard
							key={resource.key}
							resource={resource}
							onOpen={onOpen}
							onPin={onPin}
							busy={busy}
						/>
					))}
				</div>
			) : (
				<ResourceList
					resources={visible}
					onOpen={onOpen}
					onPin={onPin}
					busy={busy}
				/>
			)}
			{total > 12 && (
				<ListPagination
					offset={page * 12}
					limit={12}
					total={total}
					onPageChange={onPageChange}
				/>
			)}
		</section>
	);
}
