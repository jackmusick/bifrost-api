import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { dockVariants, windowTransition } from "./animations";
import { WindowDockItem } from "./WindowDockItem";
import type { DockItem } from "./types";

interface WindowDockProps {
	/** Items to display in the dock */
	items: DockItem[];
}

/**
 * Unified dock bar for all minimized windows.
 * Appears fixed at bottom-right when any items are present.
 */
export function WindowDock({ items }: WindowDockProps) {
	const reduceMotion = useReducedMotion();
	if (items.length === 0) {
		return null;
	}

	return (
		<motion.div
			className="fixed bottom-4 right-4 left-4 z-50 flex flex-wrap justify-end gap-2 sm:left-auto sm:max-w-[calc(100vw-2rem)]"
			variants={dockVariants}
			initial={reduceMotion ? false : "hidden"}
			animate="visible"
			transition={reduceMotion ? { duration: 0 } : windowTransition}
		>
			<AnimatePresence mode="popLayout">
				{items.map((item) => (
					<WindowDockItem key={item.id} {...item} />
				))}
			</AnimatePresence>
		</motion.div>
	);
}
