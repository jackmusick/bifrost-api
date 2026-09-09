import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { CatalogFilters } from "./CatalogFilters";
it("selects a resource category without making counts part of its accessible name", async () => {
	const onChange = vi.fn();
	const { user } = renderWithProviders(
		<CatalogFilters value="all" resources={[]} onChange={onChange} />,
	);
	expect(screen.getByRole("button", { name: "All" })).toHaveAttribute(
		"aria-pressed",
		"true",
	);
	await user.click(screen.getByRole("button", { name: "Apps" }));
	expect(onChange).toHaveBeenCalledWith("app");
});
