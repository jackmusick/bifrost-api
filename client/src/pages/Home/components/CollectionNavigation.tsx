import { useCallback, useEffect, useRef, useState } from "react";
import {
	draggable,
	dropTargetForElements,
} from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { ArrowLeft, ArrowRight, ChevronDown, Folder, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuSeparator,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
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
	onEdit,
	onDelete,
	onReorder,
}: {
	collections: HomeCollection[];
	selected: string | null;
	onSelect: (id: string | null) => void;
	onCreate: () => void;
	onEdit?: (collection: HomeCollection) => void;
	onDelete?: (collection: HomeCollection) => void;
	onReorder?: (ids: string[]) => void;
}) {
	const visible = collections.slice(0, 3);
	const selectedCollection = collections.find((c) => c.id === selected);
	if (
		selectedCollection &&
		!visible.some((c) => c.id === selectedCollection.id)
	) {
		visible.push(selectedCollection);
	}
	const overflow = collections.filter(
		(c) => !visible.some((v) => v.id === c.id),
	);
	const moveCollection = useCallback(
		(id: string, direction: -1 | 1) => {
			const from = collections.findIndex((c) => c.id === id);
			const to = from + direction;
			if (from < 0 || to < 0 || to >= collections.length) return;

			const next = [...collections];
			const [moved] = next.splice(from, 1);
			next.splice(to, 0, moved);
			onReorder?.(next.map((c) => c.id));
		},
		[collections, onReorder],
	);
	const moveToIndex = useCallback(
		(id: string, to: number) => {
			const from = collections.findIndex((c) => c.id === id);
			if (from < 0 || from === to) return;

			const next = [...collections];
			const [moved] = next.splice(from, 1);
			next.splice(to, 0, moved);
			onReorder?.(next.map((c) => c.id));
		},
		[collections, onReorder],
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
				{visible.map((c) => (
					<CollectionTab
						key={c.id}
						collection={c}
						index={collections.findIndex(
							(collection) => collection.id === c.id,
						)}
						count={collections.length}
						selected={selected === c.id}
						onSelect={() => onSelect(c.id)}
						onEdit={onEdit}
						onDelete={onDelete}
						onMove={moveCollection}
						onMoveToIndex={moveToIndex}
					/>
				))}
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

function CollectionTab({
	collection,
	index,
	count,
	selected,
	onSelect,
	onEdit,
	onDelete,
	onMove,
	onMoveToIndex,
}: {
	collection: HomeCollection;
	index: number;
	count: number;
	selected: boolean;
	onSelect: () => void;
	onEdit?: (collection: HomeCollection) => void;
	onDelete?: (collection: HomeCollection) => void;
	onMove: (id: string, direction: -1 | 1) => void;
	onMoveToIndex: (id: string, index: number) => void;
}) {
	const ref = useRef<HTMLButtonElement>(null);
	const [isDragging, setIsDragging] = useState(false);
	const [isDropTarget, setIsDropTarget] = useState(false);

	useEffect(() => {
		const element = ref.current;
		if (!element) return;

		return combine(
			draggable({
				element,
				getInitialData: () => ({
					collectionId: collection.id,
					index,
					type: "collection-tab",
				}),
				onDragStart: () => setIsDragging(true),
				onDrop: () => setIsDragging(false),
			}),
			dropTargetForElements({
				element,
				getData: () => ({ index, type: "collection-tab" }),
				canDrop: ({ source }) =>
					source.data["type"] === "collection-tab" &&
					source.data["collectionId"] !== collection.id,
				onDragEnter: () => setIsDropTarget(true),
				onDragLeave: () => setIsDropTarget(false),
				onDrop: ({ source }) => {
					setIsDropTarget(false);
					const collectionId = source.data["collectionId"];
					if (typeof collectionId === "string") {
						onMoveToIndex(collectionId, index);
					}
				},
			}),
		);
	}, [collection.id, index, onMoveToIndex]);

	return (
		<ContextMenu>
			<ContextMenuTrigger asChild>
				<button
					ref={ref}
					type="button"
					aria-current={selected ? "page" : undefined}
					onClick={onSelect}
					onKeyDown={(event) => {
						if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
							event.preventDefault();
							const rect = event.currentTarget.getBoundingClientRect();
							event.currentTarget.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: rect.left, clientY: rect.bottom }));
						}
					}}
					className={cn(
						"min-h-11 max-w-44 shrink-0 truncate border-b-2 px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-ring",
						selected
							? "border-primary text-primary font-medium"
							: "border-transparent text-muted-foreground hover:text-foreground",
						isDragging && "opacity-50",
						isDropTarget && "bg-primary/10 border-primary",
					)}
				>
					{collection.name}
				</button>
			</ContextMenuTrigger>
			<ContextMenuContent className="w-48">
				<ContextMenuItem
					disabled={index === 0}
					onSelect={() => onMove(collection.id, -1)}
				>
					<ArrowLeft className="size-4" />
					Move left
				</ContextMenuItem>
				<ContextMenuItem
					disabled={index >= count - 1}
					onSelect={() => onMove(collection.id, 1)}
				>
					<ArrowRight className="size-4" />
					Move right
				</ContextMenuItem>
				{collection.can_edit && (
					<>
						<ContextMenuSeparator />
						<ContextMenuItem onSelect={() => onEdit?.(collection)}>
							<Pencil className="size-4" />
							Edit
						</ContextMenuItem>
						<ContextMenuItem
							variant="destructive"
							onSelect={() => onDelete?.(collection)}
						>
							<Trash2 className="size-4" />
							Delete
						</ContextMenuItem>
					</>
				)}
			</ContextMenuContent>
		</ContextMenu>
	);
}
