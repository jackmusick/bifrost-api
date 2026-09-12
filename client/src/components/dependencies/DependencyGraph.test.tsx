import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";

const reactFlowCalls: Array<Record<string, unknown>> = [];
const miniMapCalls: Array<Record<string, unknown>> = [];

vi.mock("framer-motion", () => ({
	useReducedMotion: vi.fn(() => false),
}));

vi.mock("./EntityNode", () => ({
	EntityNode: () => <div data-testid="entity-node" />,
	ENTITY_TYPE_THEME: {
		workflow: {
			label: "Workflow",
			accent: "var(--chart-1)",
			accentSoft: "color-mix(in srgb, var(--chart-1) 14%, var(--background))",
			accentBorder: "color-mix(in srgb, var(--chart-1) 34%, var(--border))",
			iconColor: "var(--chart-1)",
			Icon: () => null,
		},
		form: {
			label: "Form",
			accent: "var(--chart-2)",
			accentSoft: "color-mix(in srgb, var(--chart-2) 14%, var(--background))",
			accentBorder: "color-mix(in srgb, var(--chart-2) 34%, var(--border))",
			iconColor: "var(--chart-2)",
			Icon: () => null,
		},
		app: {
			label: "App",
			accent: "var(--chart-4)",
			accentSoft: "color-mix(in srgb, var(--chart-4) 14%, var(--background))",
			accentBorder: "color-mix(in srgb, var(--chart-4) 34%, var(--border))",
			iconColor: "var(--chart-4)",
			Icon: () => null,
		},
		agent: {
			label: "Agent",
			accent: "var(--chart-5)",
			accentSoft: "color-mix(in srgb, var(--chart-5) 14%, var(--background))",
			accentBorder: "color-mix(in srgb, var(--chart-5) 34%, var(--border))",
			iconColor: "var(--chart-5)",
			Icon: () => null,
		},
	},
}));

// Viewport fitting and toolbar interactions have dedicated component tests.
vi.mock("./DependencyGraphViewport", () => ({ DependencyGraphViewport: () => null }));
vi.mock("./DependencyGraphControls", () => ({ DependencyGraphControls: () => null }));

vi.mock("@xyflow/react", () => ({
	ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
	ReactFlow: (props: Record<string, unknown> & { children?: React.ReactNode }) => {
		reactFlowCalls.push(props);
		return <div data-testid="react-flow">{props.children}</div>;
	},
	Background: (props: Record<string, unknown>) => (
		<div data-testid="background" {...props} />
	),
	Controls: ({ showInteractive: _showInteractive, ...props }: Record<string, unknown>) => (
		<div data-testid="controls" {...props} />
	),
	MiniMap: (props: Record<string, unknown>) => {
		miniMapCalls.push(props);
		return <div data-testid="minimap" />;
	},
	useNodesState: (nodes: unknown) => [nodes, vi.fn(), vi.fn()],
	useEdgesState: (edges: unknown) => [edges, vi.fn(), vi.fn()],
	MarkerType: { ArrowClosed: "ArrowClosed" },
}));

import { DependencyGraph } from "./DependencyGraph";
import { useReducedMotion } from "framer-motion";

const nodes = [
	{ id: "workflow-1", name: "Workflow", type: "workflow", org_id: null },
	{ id: "form-1", name: "Form", type: "form", org_id: null },
	{ id: "app-1", name: "App", type: "app", org_id: null },
	{ id: "agent-1", name: "Agent", type: "agent", org_id: null },
] as const;

const edges = [
	{ source: "workflow-1", target: "form-1", relationship: "uses" },
	{ source: "form-1", target: "app-1", relationship: "triggers" },
	{ source: "app-1", target: "agent-1", relationship: "invokes" },
] as const;

beforeEach(() => {
	reactFlowCalls.length = 0;
	miniMapCalls.length = 0;
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("DependencyGraph", () => {
	it("applies semantic token colors to edges and minimap nodes", () => {
		render(
			<DependencyGraph
				nodes={nodes as never}
				edges={edges as never}
				rootId="workflow-1"
			/>,
		);

		const props = reactFlowCalls.at(-1);
		expect(props).toBeDefined();

		const renderedEdges = props?.edges as Array<Record<string, unknown>>;
		expect(renderedEdges).toHaveLength(3);
		expect(renderedEdges[0].animated).toBe(true);
		expect(renderedEdges[0].style).toEqual(
			expect.objectContaining({ stroke: "var(--chart-1)" }),
		);
		expect(renderedEdges[0].markerEnd).toEqual(
			expect.objectContaining({ color: "var(--chart-1)" }),
		);
		expect(renderedEdges[1].style).toEqual(
			expect.objectContaining({ stroke: "var(--chart-2)" }),
		);
		expect(renderedEdges[2].style).toEqual(
			expect.objectContaining({ stroke: "var(--chart-4)" }),
		);
		expect(renderedEdges[2].markerEnd).toEqual(
			expect.objectContaining({ color: "var(--chart-4)" }),
		);

		expect(miniMapCalls.at(-1)).toEqual(
			expect.objectContaining({
				maskColor: "color-mix(in srgb, var(--background) 74%, transparent)",
			}),
		);
	});

	it("disables edge animation when reduced motion is preferred", async () => {
		vi.mocked(useReducedMotion).mockReturnValue(true);

		render(
			<DependencyGraph
				nodes={nodes as never}
				edges={edges as never}
				rootId="workflow-1"
			/>,
		);

		await waitFor(() => {
			const props = reactFlowCalls.at(-1);
			expect((props?.edges as Array<Record<string, unknown>>)?.[0]?.animated).toBe(
				false,
			);
		});
	});
});
