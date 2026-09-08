import { render } from "@testing-library/react";
import { expect,it,vi } from "vitest";
import { DependencyGraphViewport } from "./DependencyGraphViewport";

const data = vi.hoisted(() => ({
	width: 300,
	height: 500,
	initialized: true,
	nodes: [{ id: "root" }] as Array<{ id: string }>,
	fitView: vi.fn(),
}));

vi.mock("@xyflow/react", () => ({
	useStore: (selector: (state: typeof data) => unknown) => selector(data),
	useNodesInitialized: () => data.initialized,
	useReactFlow: () => ({ fitView: data.fitView }),
}));

it("refits resized canvases and graph data changes without re-running on unchanged renders", () => {
	const { rerender } = render(<DependencyGraphViewport />);

	expect(data.fitView).toHaveBeenCalledTimes(1);

	rerender(<DependencyGraphViewport />);
	expect(data.fitView).toHaveBeenCalledTimes(1);

	data.height = 300;
	rerender(<DependencyGraphViewport />);
	expect(data.fitView).toHaveBeenCalledTimes(2);
	expect(data.fitView).toHaveBeenLastCalledWith({
		padding: 0.2,
		maxZoom: 1.5,
		duration: 0,
	});

	data.height = 500;
	data.nodes = [...data.nodes, { id: "child" }];
	rerender(<DependencyGraphViewport />);
	expect(data.fitView).toHaveBeenCalledTimes(3);

	data.height = 0;
	rerender(<DependencyGraphViewport />);
	expect(data.fitView).toHaveBeenCalledTimes(3);
});
