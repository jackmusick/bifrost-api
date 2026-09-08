import { useEffect } from "react";
import { useNodesInitialized, useReactFlow, useStore } from "@xyflow/react";

/** Refit when available canvas space changes, without resetting ordinary user pan/zoom. */
export function DependencyGraphViewport() {
	const width = useStore((state) => state.width);
	const height = useStore((state) => state.height);
	const nodeSignature = useStore((state) =>
		state.nodes.map((node) => node.id).join("|"),
	);
	const initialized = useNodesInitialized();
	const { fitView } = useReactFlow();
	useEffect(() => {
		if (initialized && width > 0 && height > 0 && nodeSignature.length > 0)
			void fitView({ padding: 0.2, maxZoom: 1.5, duration: 0 });
	}, [width, height, nodeSignature, initialized, fitView]);
	return null;
}
