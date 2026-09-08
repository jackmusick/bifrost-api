// client/src/components/window-management/WindowOverlay.tsx

import { motion, useReducedMotion } from "framer-motion";
import { overlayVariants, windowTransition } from "./animations";

interface WindowOverlayProps {
	children: React.ReactNode;
}

/**
 * Animated fullscreen overlay wrapper for maximized windows.
 * Provides consistent enter/exit animations.
 */
export function WindowOverlay({ children }: WindowOverlayProps) {
	const reduceMotion = useReducedMotion();
	return (
		<motion.div
			className="fixed inset-0 z-[100] bg-background"
			variants={overlayVariants}
			initial={reduceMotion ? false : "hidden"}
			animate="visible"
			exit="hidden"
			transition={reduceMotion ? { duration: 0 } : windowTransition}
			style={{ originX: 1, originY: 1 }}
		>
			{children}
		</motion.div>
	);
}
