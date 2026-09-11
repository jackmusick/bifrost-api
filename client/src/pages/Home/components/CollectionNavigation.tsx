import { ChevronDown, Folder, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getIcon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { HomeCollection } from "@/services/home";

/** Collection links filter the same catalog; membership never changes access. */
export function CollectionNavigation({
	collections,
	selected,
	onSelect,
	onCreate,
}: {
	collections: HomeCollection[];
	selected: string | null;
	onSelect: (id: string | null) => void;
	onCreate: () => void;
}) {
	const active = collections.find((c) => c.id === selected);
	const visible = collections.slice(0, 3);
	if (active && !visible.some((c) => c.id === selected))
		visible.splice(2, 1, active);
	const overflow = collections.filter(
		(c) => !visible.some((v) => v.id === c.id),
	);
	const link = (id: string | null, name: string) => (
		<button
			key={id ?? "all"}
			type="button"
			aria-current={selected === id ? "page" : undefined}
			onClick={() => onSelect(id)}
			className={cn(
				"min-h-11 max-w-44 shrink-0 truncate border-b-2 px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-ring",
				selected === id
					? "border-primary text-primary font-medium"
					: "border-transparent text-muted-foreground hover:text-foreground",
			)}
		>
			{name}
		</button>
	);
	return (
		<nav
			aria-label="Collections"
			className="flex min-w-0 items-center border-b"
		>
			<div className="flex min-w-0 flex-1 items-center overflow-x-auto">
				{link(null, "All")}
				{visible.map((c) => link(c.id, c.name))}
			</div>
			{overflow.length > 0 && (
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Button
							variant="ghost"
							size="sm"
							aria-label="More collections"
						>
							<ChevronDown className="size-4" />
							<span className="hidden sm:inline">More</span>
						</Button>
					</DropdownMenuTrigger>
					<DropdownMenuContent
						align="end"
						className="w-64 max-h-80 overflow-y-auto"
					>
						{overflow.map((c) => {
							const Icon = getIcon(c.icon, Folder);
							return (
								<DropdownMenuItem
									key={c.id}
									onSelect={() => onSelect(c.id)}
								>
									<Icon className="size-4 shrink-0" />
									<span className="min-w-0 whitespace-normal break-words">
										{c.name}
									</span>
								</DropdownMenuItem>
							);
						})}
					</DropdownMenuContent>
				</DropdownMenu>
			)}
			<Button
				variant="ghost"
				size="icon"
				aria-label="New collection"
				onClick={onCreate}
				className="shrink-0"
			>
				<Plus className="size-4" />
			</Button>
		</nav>
	);
}
