import { beforeEach, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { CollectionNavigation } from "./CollectionNavigation";
import type { HomeCollection } from "@/services/home";

const dragRegistrations: Array<{
	data: Record<string, unknown>;
	onDragStart?: () => void;
	onDrop?: (args?: unknown) => void;
}> = [];
const dropRegistrations: Array<{
	data: Record<string, unknown>;
	onDrop?: (args: { source: { data: Record<string, unknown> } }) => void;
}> = [];

vi.mock("@atlaskit/pragmatic-drag-and-drop/element/adapter", () => ({
	draggable: vi.fn((config) => {
		dragRegistrations.push({
			data: config.getInitialData(),
			onDragStart: config.onDragStart,
			onDrop: config.onDrop,
		});
		return () => {};
	}),
	dropTargetForElements: vi.fn((config) => {
		dropRegistrations.push({
			data: config.getData(),
			onDrop: config.onDrop,
		});
		return () => {};
	}),
}));

vi.mock("@atlaskit/pragmatic-drag-and-drop/combine", () => ({
	combine:
		(...cleanups: Array<() => void>) =>
		() => {
			cleanups.forEach((cleanup) => cleanup());
		},
}));

beforeEach(() => {
	dragRegistrations.length = 0;
	dropRegistrations.length = 0;
});

function makeCollections(count: number): HomeCollection[] {
	return Array.from({ length: count }, (_, i) =>
		makeCollection({ id: String(i), name: `Collection ${i}` }),
	);
}

function makeCollection(
	overrides: Partial<HomeCollection> = {},
): HomeCollection {
	return {
		id: "collection",
		name: "Collection",
		icon: "folder",
		shared: false,
		can_edit: true,
		resource_keys: [],
		organization_id: null,
		organization_name: null,
		description: "",
		...overrides,
	};
}

it("keeps selected overflow collection reachable as a tab and returns to All", async () => {
	const collections = makeCollections(6);
	const onSelect = vi.fn();
	const onCreate = vi.fn();
	const { user, rerender } = renderWithProviders(
		<CollectionNavigation
			collections={collections}
			selected={null}
			onSelect={onSelect}
			onCreate={onCreate}
		/>,
	);
	await user.click(screen.getByRole("button", { name: "More collections" }));
	await user.click(screen.getByRole("menuitem", { name: "Collection 5" }));
	expect(onSelect).toHaveBeenCalledWith("5");
	rerender(
		<CollectionNavigation
			collections={collections}
			selected="5"
			onSelect={onSelect}
			onCreate={onCreate}
		/>,
	);
	expect(
		screen.getByRole("button", { name: "Collection 5" }),
	).toHaveAttribute("aria-current", "page");
	expect(
		screen.queryByRole("menuitem", { name: "Collection 5" }),
	).not.toBeInTheDocument();
	await user.keyboard("{Escape}");
	await user.click(screen.getByRole("button", { name: "All" }));
	expect(onSelect).toHaveBeenLastCalledWith(null);
	await user.click(screen.getByRole("button", { name: "New collection" }));
	expect(onCreate).toHaveBeenCalledOnce();
});

it("shows edit and delete only for editable collections", async () => {
	const editable = makeCollection({
		id: "editable",
		name: "Editable",
		can_edit: true,
	});
	const shared = makeCollection({
		id: "shared",
		name: "Shared",
		can_edit: false,
		shared: true,
	});
	const onEdit = vi.fn();
	const onDelete = vi.fn();
	const { user } = renderWithProviders(
		<CollectionNavigation
			collections={[editable, shared]}
			selected={null}
			onSelect={vi.fn()}
			onCreate={vi.fn()}
			onEdit={onEdit}
			onDelete={onDelete}
			onReorder={vi.fn()}
		/>,
	);

	await user.pointer({
		keys: "[MouseRight]",
		target: screen.getByRole("button", { name: "Editable" }),
	});
	await user.click(screen.getByRole("menuitem", { name: "Edit" }));
	expect(onEdit).toHaveBeenCalledWith(editable);

	await user.pointer({
		keys: "[MouseRight]",
		target: screen.getByRole("button", { name: "Editable" }),
	});
	await user.click(screen.getByRole("menuitem", { name: "Delete" }));
	expect(onDelete).toHaveBeenCalledWith(editable);

	await user.pointer({
		keys: "[MouseRight]",
		target: screen.getByRole("button", { name: "Shared" }),
	});
	expect(
		screen.queryByRole("menuitem", { name: "Edit" }),
	).not.toBeInTheDocument();
	expect(
		screen.queryByRole("menuitem", { name: "Delete" }),
	).not.toBeInTheDocument();
});

it("reorders editable and shared collections from the context menu", async () => {
	const collections = [
		makeCollection({ id: "first", name: "First", can_edit: true }),
		makeCollection({
			id: "second",
			name: "Second",
			can_edit: false,
			shared: true,
		}),
		makeCollection({ id: "third", name: "Third", can_edit: true }),
	];
	const onReorder = vi.fn();
	const { user } = renderWithProviders(
		<CollectionNavigation
			collections={collections}
			selected={null}
			onSelect={vi.fn()}
			onCreate={vi.fn()}
			onReorder={onReorder}
		/>,
	);

	await user.pointer({
		keys: "[MouseRight]",
		target: screen.getByRole("button", { name: "Second" }),
	});
	await user.click(screen.getByRole("menuitem", { name: "Move left" }));
	expect(onReorder).toHaveBeenCalledWith(["second", "first", "third"]);

	await user.pointer({
		keys: "[MouseRight]",
		target: screen.getByRole("button", { name: "Second" }),
	});
	await user.click(screen.getByRole("menuitem", { name: "Move right" }));
	expect(onReorder).toHaveBeenLastCalledWith(["first", "third", "second"]);
});

it("reorders visible collection tabs when a dragged tab drops on another tab", () => {
	const onReorder = vi.fn();
	renderWithProviders(
		<CollectionNavigation
			collections={makeCollections(3)}
			selected={null}
			onSelect={vi.fn()}
			onCreate={vi.fn()}
			onReorder={onReorder}
		/>,
	);

	expect(dragRegistrations.map((registration) => registration.data)).toEqual([
		expect.objectContaining({ collectionId: "0", index: 0 }),
		expect.objectContaining({ collectionId: "1", index: 1 }),
		expect.objectContaining({ collectionId: "2", index: 2 }),
	]);

	dropRegistrations[2].onDrop?.({
		source: { data: { collectionId: "0", type: "collection-tab" } },
	});

	expect(onReorder).toHaveBeenCalledWith(["1", "2", "0"]);
});
