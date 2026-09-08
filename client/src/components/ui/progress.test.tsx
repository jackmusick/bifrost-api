import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Progress } from "./progress";

describe("Progress value contract", () => {
	it("exposes real values and custom maximums while matching the visible fraction", () => {
		const { rerender } = render(
			<Progress aria-label="Upload" value={15} max={20} />,
		);
		const bar = screen.getByRole("progressbar", { name: "Upload" });
		expect(bar).toHaveAttribute("aria-valuenow", "15");
		expect(bar).toHaveAttribute("aria-valuemax", "20");
		expect(bar.firstElementChild).toHaveStyle({
			transform: "translateX(-25%)",
		});
		rerender(<Progress aria-label="Upload" value={20} max={20} />);
		expect(bar).toHaveAttribute("data-state", "complete");
		expect(bar.firstElementChild).toHaveStyle({
			transform: "translateX(-0%)",
		});
	});
	it("represents unknown progress without inventing a percentage", () => {
		const { rerender } = render(<Progress aria-label="Processing" />);
		const bar = screen.getByRole("progressbar", { name: "Processing" });
		expect(bar).toHaveAttribute("data-state", "indeterminate");
		expect(bar).not.toHaveAttribute("aria-valuenow");
		rerender(<Progress aria-label="Processing" value={0} />);
		expect(bar).toHaveAttribute("aria-valuenow", "0");
		expect(bar).toHaveAttribute("data-state", "loading");
	});
});
