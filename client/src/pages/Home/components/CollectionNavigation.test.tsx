import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { CollectionNavigation } from "./CollectionNavigation";
import type { HomeCollection } from "@/services/home";

it("keeps collection overflow reachable and returns to All", async () => {
	const collections = Array.from(
		{ length: 6 },
		(_, i) =>
			({
				id: String(i),
				name: `Collection ${i}`,
				icon: "folder",
				shared: false,
				can_edit: true,
				resource_keys: [],
				organization_id: null,
				organization_name: null,
				description: "",
			}) satisfies HomeCollection,
	);
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
	await user.click(screen.getByRole("button", { name: "All" }));
	expect(onSelect).toHaveBeenLastCalledWith(null);
	await user.click(screen.getByRole("button", { name: "New collection" }));
	expect(onCreate).toHaveBeenCalledOnce();
});
