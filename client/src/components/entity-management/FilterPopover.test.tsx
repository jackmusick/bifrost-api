import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { FilterPopover } from "./FilterPopover";
import type { Organization } from "./types";

it("keeps equal labels in different filter groups independent and shows current filters", async () => {
	const user = userEvent.setup();
	const props = { typeFilter: "workflow", setTypeFilter: vi.fn(), orgFilter: "all", setOrgFilter: vi.fn(), accessFilter: "all", setAccessFilter: vi.fn(), usageFilter: "all", setUsageFilter: vi.fn(), organizations: [{ id: "org", name: "Workflows" }] as Organization[], activeFilterCount: 1, onClearFilters: vi.fn() };
	render(<FilterPopover {...props} />);
	await user.click(screen.getByRole("button", { name: "Filters (1 active)" }));
	await user.type(screen.getByRole("combobox", { name: "Search filters" }), "Workflows");
	const options = screen.getAllByRole("option", { name: /Workflows/ });
	expect(options).toHaveLength(2);
	expect(options[0]).toHaveTextContent("Current filter");
	await user.click(options[1]);
	expect(props.setOrgFilter).toHaveBeenCalledWith("org");
	expect(props.setTypeFilter).not.toHaveBeenCalled();
	await user.click(screen.getByRole("button", { name: "Clear all filters" }));
	expect(props.onClearFilters).toHaveBeenCalledOnce();
	expect(screen.queryByRole("combobox", { name: "Search filters" })).not.toBeInTheDocument();
});
