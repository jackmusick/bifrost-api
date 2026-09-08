import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { EntityCard } from "./EntityCard";
import type { EntityWithScope } from "./types";
vi.mock("@atlaskit/pragmatic-drag-and-drop/element/adapter", () => ({
	draggable: () => () => {},
}));
const entity = {
	id: "test",
	name: "Review workflow",
	entityType: "workflow",
	organizationId: null,
	accessLevel: "authenticated",
	createdAt: "2026-09-08",
	usedByCount: 1,
	original: {},
} as EntityWithScope;
function show(managed = false) {
	const onShowRelationships = vi.fn();
	render(
		<EntityCard
			entity={{
				...entity,
				original: { ...entity.original, is_solution_managed: managed },
			}}
			selected={false}
			onSelect={vi.fn()}
			onShowRelationships={onShowRelationships}
			onDelete={vi.fn()}
			organizations={[]}
			selectedIds={new Set()}
			allEntities={[entity]}
		/>,
	);
	return onShowRelationships;
}
describe("EntityCard actions", () => {
	it("offers dependencies directly without opening overflow", () => {
		const callback = show();
		fireEvent.click(
			screen.getByRole("button", {
				name: "Show dependencies for Review workflow",
			}),
		);
		expect(callback).toHaveBeenCalledWith(
			"test",
			"workflow",
			"Review workflow",
		);
		expect(
			screen.getByRole("button", {
				name: "More actions for Review workflow",
			}),
		).toBeInTheDocument();
	});
	it("keeps dependencies available on managed entities without a destructive menu", () => {
		show(true);
		expect(
			screen.getByRole("button", {
				name: "Show dependencies for Review workflow",
			}),
		).toBeEnabled();
		expect(
			screen.queryByRole("button", {
				name: "More actions for Review workflow",
			}),
		).not.toBeInTheDocument();
	});
});
