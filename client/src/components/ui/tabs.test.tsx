import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

function Example({ orientation }: { orientation?: "horizontal" | "vertical" }) {
	return (
		<Tabs defaultValue="overview" orientation={orientation}>
			<TabsList aria-label="Execution sections">
				<TabsTrigger value="overview">Overview</TabsTrigger>
				<TabsTrigger value="unavailable" disabled>Unavailable</TabsTrigger>
				<TabsTrigger value="logs">Logs</TabsTrigger>
			</TabsList>
			<TabsContent value="overview">Overview content</TabsContent>
			<TabsContent value="logs">Log content</TabsContent>
		</Tabs>
	);
}

describe("Tabs orientation contract", () => {
	it.each([
		["vertical", "{ArrowDown}", "{ArrowUp}"],
		["horizontal", "{ArrowRight}", "{ArrowLeft}"],
	] as const)("uses %s arrow navigation and skips disabled tabs", async (orientation, forward, backward) => {
		const user = userEvent.setup();
		render(<Example orientation={orientation} />);
		expect(screen.getByRole("tablist")).toHaveAttribute("aria-orientation", orientation);
		const overview = screen.getByRole("tab", { name: "Overview" });
		const logs = screen.getByRole("tab", { name: "Logs" });
		overview.focus();
		await user.keyboard(forward);
		expect(logs).toHaveFocus();
		expect(logs).toHaveAttribute("aria-selected", "true");
		expect(screen.getByRole("tabpanel")).toHaveTextContent("Log content");
		await user.keyboard(backward);
		expect(overview).toHaveFocus();
		expect(overview).toHaveAttribute("aria-selected", "true");
	});

	it("preserves horizontal navigation when orientation is omitted", async () => {
		const user = userEvent.setup();
		render(<Example />);
		expect(screen.getByRole("tablist")).toHaveAttribute("aria-orientation", "horizontal");
		screen.getByRole("tab", { name: "Overview" }).focus();
		await user.keyboard("{ArrowRight}");
		expect(screen.getByRole("tab", { name: "Logs" })).toHaveFocus();
	});
});
