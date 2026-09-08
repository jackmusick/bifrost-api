import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ModelPricingList } from "./ModelPricingList";
import type { AIModelPricingListItem } from "@/services/ai-pricing";

function makeItem(overrides: Partial<AIModelPricingListItem> = {}): AIModelPricingListItem {
	return {
		id: 1,
		model: "gpt-4.1",
		provider: "openai",
		input_price_per_million: "5.00",
		output_price_per_million: "15.00",
		effective_date: "2026-09-01",
		created_at: "2026-09-01T00:00:00Z",
		updated_at: "2026-09-01T00:00:00Z",
		cache_read_price_per_million: null,
		cache_write_price_per_million: null,
		is_used: true,
		...overrides,
	};
}

describe("ModelPricingList", () => {
	it("opens edit from the model name and from the record actions menu", async () => {
		const onEdit = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<ModelPricingList items={[makeItem()]} onEdit={onEdit} onDelete={onDelete} />,
		);

		await user.click(screen.getByRole("button", { name: "Edit gpt-4.1" }));
		expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ model: "gpt-4.1" }));

		await user.click(screen.getByRole("button", { name: "More actions for gpt-4.1" }));
		await user.click(screen.getByRole("menuitem", { name: "Edit" }));
		expect(onEdit).toHaveBeenCalledTimes(2);
		expect(onDelete).not.toHaveBeenCalled();
	});

	it("routes delete through the record actions menu with keyboard selection", async () => {
		const onEdit = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<ModelPricingList items={[makeItem()]} onEdit={onEdit} onDelete={onDelete} />,
		);

		await user.click(screen.getByRole("button", { name: "More actions for gpt-4.1" }));
		const firstItem = screen.getByRole("menuitem", { name: "Edit" });
		firstItem.focus();
		await user.keyboard("{ArrowDown}{Enter}");
		expect(onDelete).toHaveBeenCalledWith(expect.objectContaining({ model: "gpt-4.1" }));
		expect(onEdit).not.toHaveBeenCalled();
	});
});
