import { LayoutGrid, List, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ListPagination } from "@/components/pagination/ListPagination";
import type { HomeCollection, HomeResource } from "@/services/home";
import { ResourceCard } from "./ResourceCard";
import { ResourceList } from "./ResourceList";
export function HomeBrowse({
	selected,
	total,
	grid,
	kind,
	visible,
	resourceCount,
	busy,
	page,
	updateParam,
	onOpen,
	onPin,
	onPageChange,
}: {
	selected?: HomeCollection;
	total: number;
	grid: boolean;
	kind: string;
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
				<div className="flex min-w-0 items-center gap-2">
					<h2 className="text-base font-semibold [overflow-wrap:anywhere]">
						{selected?.name ?? "Browse"}
					</h2>
					<span className="shrink-0 text-xs text-muted-foreground">
						{total} resources
					</span>
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
				<div className="flex gap-1">
					<Button
						size="icon"
						variant={grid ? "ghost" : "secondary"}
						aria-label="List view"
						aria-pressed={!grid}
						onClick={() => updateParam("view", null)}
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
			<Tabs
				value={kind}
				onValueChange={(value) => updateParam("type", value)}
			>
				<TabsList>
					<TabsTrigger value="all">All</TabsTrigger>
					<TabsTrigger value="app">Apps</TabsTrigger>
					<TabsTrigger value="form">Forms</TabsTrigger>
					<TabsTrigger value="agent">Agents</TabsTrigger>
				</TabsList>
			</Tabs>
			{visible.length === 0 ? (
				<p className="rounded border border-dashed p-6 text-sm text-muted-foreground">
					{resourceCount
						? "No resources match these filters. Try another search or collection."
						: "No launchable resources are available yet. Published apps, active forms, and chat agents will appear here when you have access."}
				</p>
			) : grid ? (
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
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
