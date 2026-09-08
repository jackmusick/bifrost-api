import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const dependencyGraphCalls: Array<Record<string, unknown>> = [];

vi.mock("@/components/dependencies/DependencyGraph", () => ({
	DEPENDENCY_GRAPH_LEGEND: [
		{
			entityType: "workflow",
			label: "Workflow",
			color: "var(--bf-info)",
			softColor: "var(--bf-info-soft)",
		},
		{
			entityType: "form",
			label: "Form",
			color: "var(--bf-success)",
			softColor: "var(--bf-success-soft)",
		},
	],
	DependencyGraph: (props: Record<string, unknown>) => {
		dependencyGraphCalls.push(props);
		return <div data-testid="dependency-graph" />;
	},
}));

import { DependencyGraphDialog } from "./DependencyGraphDialog";

beforeEach(() => {
	dependencyGraphCalls.length = 0;
});

describe("DependencyGraphDialog", () => {
	it("uses responsive dialog sizing and keeps the legend outside the graph canvas", () => {
		render(
			<DependencyGraphDialog
				open
				onOpenChange={() => {}}
				entityName="Sample App"
				entityType="app"
				graphData={{
					root_id: "root-1",
					nodes: [
						{ id: "root-1", name: "Root", type: "app", org_id: null },
					] as never,
					edges: [] as never,
				}}
				isLoading={false}
			/>,
		);

		const content = document.querySelector('[data-slot="dialog-content"]');
		expect(content).not.toBeNull();
		expect(content?.className).toContain("w-[calc(100vw-1rem)]");
		expect(content?.className).toContain("h-[calc(100dvh-1rem)]");
		expect(content?.className).toContain("sm:max-w-none");
		expect(content?.className).toContain("sm:w-[min(92vw,72rem)]");
		expect(content?.className).toContain("sm:h-[min(88vh,52rem)]");
		expect(content?.querySelector('[class*="grid-rows-[minmax(0,1fr)_auto]"]')).not.toBeNull();
		expect(screen.getByTestId("dependency-graph")).toBeInTheDocument();
		expect(screen.getAllByText("Legend").some((node) => node.closest("details"))).toBe(
			true,
		);
		expect(screen.getAllByText("Workflow").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Form").length).toBeGreaterThan(0);

		expect(dependencyGraphCalls.at(-1)).toEqual(
			expect.objectContaining({
				className: "h-full",
				rootId: "root-1",
			}),
		);
	});

	it("renders the loading and empty states without the legend overlaying the graph area", () => {
		render(
			<DependencyGraphDialog
				open
				onOpenChange={() => {}}
				entityName="Sample App"
				entityType={null}
				graphData={null}
				isLoading={true}
			/>,
		);

		expect(screen.getByText(/loading dependency graph/i)).toBeInTheDocument();
		expect(screen.queryByTestId("dependency-graph")).toBeNull();
	});
});
