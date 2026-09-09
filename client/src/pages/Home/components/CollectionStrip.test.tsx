import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import type { HomeCollection } from "@/services/home";
import { CollectionStrip } from "./CollectionStrip";

const collections: HomeCollection[] = [
	{ id: "col-1", name: "Onboarding", description: "", icon: "users", shared: false, organization_id: null, resource_keys: ["app:a", "form:b"], can_edit: true, organization_name: null },
	{ id: "col-2", name: "Customer ops", description: "", icon: "briefcase-business", shared: true, organization_id: "org-1", resource_keys: ["agent:c"], can_edit: false, organization_name: "Acme" },
];

describe("CollectionStrip", () => {
	it("selects, clears, creates, and edits collections", async () => {
		const onSelect = vi.fn();
		const onEdit = vi.fn();
		const onCreate = vi.fn();
		const { user, rerender } = renderWithProviders(
			<CollectionStrip collections={collections} selected={null} onSelect={onSelect} onEdit={onEdit} onCreate={onCreate} />,
		);

		await user.click(screen.getByText("Onboarding").closest("button")!);
		expect(onSelect).toHaveBeenCalledWith("col-1");

		rerender(
			<CollectionStrip collections={collections} selected="col-1" onSelect={onSelect} onEdit={onEdit} onCreate={onCreate} />,
		);
		await user.click(screen.getByText("Onboarding").closest("button")!);
		expect(onSelect).toHaveBeenLastCalledWith(null);

		await user.click(screen.getByRole("button", { name: "Edit Onboarding" }));
		expect(onEdit).toHaveBeenCalledWith(collections[0]);
		expect(screen.queryByRole("button", { name: "Edit Customer ops" })).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "New collection" }));
		expect(onCreate).toHaveBeenCalled();
	});

	it("offers creation from the empty state", async () => {
		const onCreate = vi.fn();
		const { user } = renderWithProviders(
			<CollectionStrip collections={[]} selected={null} onSelect={vi.fn()} onEdit={vi.fn()} onCreate={onCreate} />,
		);

		await user.click(screen.getByRole("button", { name: "Create a collection" }));
		expect(onCreate).toHaveBeenCalledOnce();
	});
});
