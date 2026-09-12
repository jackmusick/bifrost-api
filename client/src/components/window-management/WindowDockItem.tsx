// client/src/components/window-management/WindowDockItem.tsx

import { motion, useReducedMotion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { dockItemVariants, windowTransition } from "./animations";
import type { DockItem } from "./types";

type WindowDockItemProps = DockItem;

/**
 * Individual item in the window dock bar.
 * Shows icon, label, and loading state.
 */
export function WindowDockItem({
	id,
	icon,
	label,
	isLoading,
	onRestore,
}: WindowDockItemProps) {
	const reduceMotion = useReducedMotion();
	return (
		<motion.button
			type="button"
			data-window-id={id}
			aria-label={`Restore ${label}`}
			layout={!reduceMotion}
			variants={dockItemVariants}
			initial={reduceMotion ? false : "hidden"}
			animate="visible"
			exit="exit"
			transition={reduceMotion ? { duration: 0 } : windowTransition}
			onClick={onRestore}
			className="flex min-h-11 min-w-0 max-w-full items-center gap-2 rounded-[var(--bf-radius-control)] border bg-background px-3 py-2 shadow-sm hover:bg-muted transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			whileHover={reduceMotion ? undefined : { scale: 1.02 }}
			whileTap={reduceMotion ? undefined : { scale: 0.98 }}
		>
			{isLoading ? (
				<Loader2 className="h-4 w-4 shrink-0 motion-safe:animate-spin text-muted-foreground" />
			) : (
				<span className="h-4 w-4 shrink-0 flex items-center justify-center text-muted-foreground">
					{icon}
				</span>
			)}
			<span className="min-w-0 text-left text-sm font-medium [overflow-wrap:anywhere]">
				{label}
			</span>
		</motion.button>
	);
}
