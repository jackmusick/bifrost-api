import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
export function KnowledgeEditorPane({
	open,
	inline,
	busy,
	children,
	onClose,
}: {
	open: boolean;
	inline: boolean;
	busy: boolean;
	children: ReactNode;
	onClose: () => void;
}) {
	const reduceMotion = useReducedMotion();
	if (!open) return null;
	return (
		<motion.aside
			role="region"
			aria-label="Knowledge document editor"
			className={
				inline
					? "relative z-20 flex min-h-0 w-[min(42vw,560px)] shrink-0 flex-col overflow-hidden border-l bg-card"
					: "absolute inset-0 z-20 flex min-h-0 flex-col overflow-hidden bg-card"
			}
			initial={
				reduceMotion
					? false
					: inline
						? { width: 0, opacity: 0 }
						: { x: "100%", opacity: 0 }
			}
			animate={
				inline
					? { width: "min(42vw, 560px)", opacity: 1 }
					: { width: "100%", x: 0, opacity: 1 }
			}
			exit={inline ? { width: 0, opacity: 0 } : { x: "100%", opacity: 0 }}
			transition={{
				duration: reduceMotion ? 0 : 0.2,
				ease: [0.22, 1, 0.36, 1],
			}}
			onKeyDown={(event) => {
				if (
					event.key === "Escape" &&
					!event.defaultPrevented &&
					!busy
				) {
					event.stopPropagation();
					onClose();
				}
			}}
		>
			{children}
		</motion.aside>
	);
}
