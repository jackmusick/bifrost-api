import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Calendar } from "./calendar";

describe("Calendar", () => {
	it("uses a full-width mobile shell while preserving multimonth rendering", () => {
		const { container } = render(
			<Calendar
				defaultMonth={new Date(2026, 8, 1)}
				numberOfMonths={2}
				showWeekNumber
			/>,
		);

		const root = container.querySelector('[data-slot="calendar"]');
		expect(root).toHaveClass("w-full", "min-w-0", "p-2");
		expect(root).toHaveClass("sm:w-fit", "sm:p-3");
		expect(screen.getAllByRole("grid")).toHaveLength(2);
	});
});
