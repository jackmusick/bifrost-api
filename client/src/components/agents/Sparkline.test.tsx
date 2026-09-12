import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Sparkline } from "./Sparkline";

describe("Sparkline", () => {
	it("renders an accessible chart for a real trend", () => {
		render(<Sparkline values={[2, 4, 1, 5]} />);
		expect(
			screen.getByRole("img", {
				name: /trend chart with 4 points/i,
			}),
		).toBeInTheDocument();
	});

	it("returns null by default when there are fewer than two points", () => {
		const { container } = render(<Sparkline values={[4]} />);
		expect(container).toBeEmptyDOMElement();
	});

	it("can render an explicit empty state when requested", () => {
		render(<Sparkline values={[4]} emptyLabel="No activity yet" />);
		expect(
			screen.getByRole("status", { name: /no activity yet/i }),
		).toBeInTheDocument();
	});
});
