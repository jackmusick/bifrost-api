import { useEffect, useRef, useState } from "react";

/** Two readable code panes need room within the comparison, not merely the viewport. */
export function useComparisonLayout() {
	const containerRef = useRef<HTMLDivElement>(null);
	const [wide, setWide] = useState(false);
	useEffect(() => {
		const element = containerRef.current;
		if (!element) return;
		const observer = new ResizeObserver(([entry]) =>
			setWide((entry?.contentRect.width ?? 0) >= 720),
		);
		observer.observe(element);
		return () => observer.disconnect();
	}, []);
	return { containerRef, wide };
}
