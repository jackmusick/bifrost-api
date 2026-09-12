import { describe, it, expect } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { TableDetailHeader } from "./TableDetailHeader";

describe("TableDetailHeader", () => {
	it("keeps the description out of navigation until requested and formats it", async () => {
		const { user } = await renderWithProviders(
			<TableDetailHeader
				name="customers"
				description="Customer **access records**."
				backTo="/tables"
				backLabel="Back to Tables"
			/>,
		);
		expect(
			screen.getByRole("link", { name: "Back to Tables" }),
		).toHaveAttribute("href", "/tables");
		expect(screen.queryByText("access records")).not.toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "About This Table" }),
		);
		expect(screen.getByText("access records").tagName).toBe("STRONG");
	});
	it("retains solution navigation without an empty description control", async () => {
		await renderWithProviders(
			<TableDetailHeader
				name="customers"
				description=""
				backTo="/solutions/s1"
				backLabel="Back to Solution"
			/>,
		);
		expect(
			screen.getByRole("link", { name: "Back to Solution" }),
		).toHaveAttribute("href", "/solutions/s1");
		expect(
			screen.queryByRole("button", { name: "About This Table" }),
		).not.toBeInTheDocument();
	});
});
