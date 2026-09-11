import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { CatalogFilters } from "./CatalogFilters";
it("selects resource types with their available counts", async () => {
	const onChange = vi.fn();
	const { user } = renderWithProviders(
		<CatalogFilters value="all" resources={[]} onChange={onChange} />,
	);
	await user.click(screen.getByRole("combobox", { name: "Resource type" }));
	await user.click(screen.getByRole("option", { name: /^Apps/ }));
	expect(onChange).toHaveBeenCalledWith("app");
});
