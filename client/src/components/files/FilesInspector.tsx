import { useEffect, useRef, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { FileText, Folder, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FilesInspectorProps {
	title: string;
	path: string;
	isFile: boolean;
	inline: boolean;
	width?: number;
	busy?: boolean;
	onClose: () => void;
	children: ReactNode;
}

/** The inspector belongs to the Files workspace, including on small screens. */
export function FilesInspector({
	title,
	path,
	isFile,
	inline,
	width = 384,
	busy = false,
	onClose,
	children,
}: FilesInspectorProps) {
	const closeRef = useRef<HTMLButtonElement>(null);
	const reduceMotion = useReducedMotion();
	useEffect(() => {
		closeRef.current?.focus({ preventScroll: true });
	}, []);
	const Icon = isFile ? FileText : Folder;
	return (
		<motion.aside
			role="region"
			aria-label="File details"
			className={
				inline
					? "relative z-20 flex min-h-0 shrink-0 flex-col overflow-hidden border-l bg-card"
					: "absolute inset-0 z-20 flex min-h-0 flex-col overflow-hidden bg-card"
			}
			initial={
				reduceMotion
					? false
					: inline
						? { width: 0, opacity: 0 }
						: { x: "100%", opacity: 0 }
			}
			animate={inline ? { width, opacity: 1 } : { x: 0, opacity: 1 }}
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
			<header className="flex shrink-0 items-start gap-3 border-b px-4 py-3">
				<Icon
					aria-hidden="true"
					className="mt-1 size-5 shrink-0 text-primary"
				/>
				<div className="min-w-0 flex-1">
					<h2 className="break-words text-sm font-semibold">
						{title}
					</h2>
					<p className="mt-1 break-words text-xs leading-5 text-muted-foreground">
						{path}
					</p>
				</div>
				<Button
					ref={closeRef}
					disabled={busy}
					variant="ghost"
					size="icon"
					aria-label="Close file details"
					onClick={onClose}
					className="shrink-0"
				>
					<X aria-hidden="true" className="size-4" />
				</Button>
			</header>
			{children}
		</motion.aside>
	);
}
