import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { JsonValuePreview } from "./JsonValuePreview";

describe("JsonValuePreview", () => {
	it("preserves complete nested JSON in a focusable scroll region", () => {
		const value = {
			nested: {
				text: "first\nsecond",
				enabled: true,
				count: 0,
				absent: null,
			},
		};
		render(<JsonValuePreview value={value} />);
		const region = screen.getByRole("region", { name: "JSON preview" });
		expect(region).toHaveAttribute("tabindex", "0");
		expect(region.textContent).toBe(JSON.stringify(value, null, 2));
	});
	it("bounds oversized JSON with an explicit preview notice", () => {
		const value = { text: "x".repeat(30000) };
		render(<JsonValuePreview value={value} />);
		expect(screen.getByText(/Showing the first 25,000/)).toBeVisible();
		expect(screen.getByRole("region").textContent).toBe(
			JSON.stringify(value, null, 2).slice(0, 25000) + "\n…",
		);
	});
});
