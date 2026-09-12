/**
 * TodoList Component
 *
 * Displays a persistent checklist from the SDK's TodoWrite tool.
 * Shows task progress with status icons and animations.
 */

import { useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Circle, CircleDot, CheckCircle2, ListTodo } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TodoItem } from "@/services/websocket";

interface TodoListProps {
	todos: TodoItem[];
	className?: string;
}

/** Status icon component with appropriate styling */
function StatusIcon({ status }: { status: TodoItem["status"] }) {
	const prefersReducedMotion = useReducedMotion();
	switch (status) {
		case "pending":
			return (
				<Circle className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
			);
		case "in_progress":
			return (
				<motion.div
					animate={prefersReducedMotion ? { rotate: 0 } : { rotate: 360 }}
					transition={{
						duration: prefersReducedMotion ? 0 : 2,
						repeat: prefersReducedMotion ? 0 : Infinity,
						ease: "linear",
					}}
				>
					<CircleDot className="h-4 w-4 flex-shrink-0 text-[var(--bf-info)]" />
				</motion.div>
			);
		case "completed":
			return (
				<CheckCircle2 className="h-4 w-4 flex-shrink-0 text-[var(--bf-success)]" />
			);
	}
}

/** Individual todo item with animation */
function TodoItemRow({ todo, index }: { todo: TodoItem; index: number }) {
	const reducedMotion = useReducedMotion();
	const isInProgress = todo.status === "in_progress";
	const isCompleted = todo.status === "completed";

	return (
		<motion.div
			initial={reducedMotion ? false : { opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			exit={reducedMotion ? { opacity: 1, x: 0 } : { opacity: 0, x: 10 }}
			transition={reducedMotion ? { duration: 0 } : { delay: index * 0.05 }}
			className={cn(
				"flex items-start gap-2 rounded-[var(--bf-radius-surface)] px-2 py-2 motion-safe:transition-colors",
				isInProgress && "bg-muted/40",
				isCompleted && "opacity-60",
			)}
		>
			<div className="mt-0.5">
				<StatusIcon status={todo.status} />
			</div>
			<div className="flex-1 min-w-0">
				<span
					className={cn(
						"text-sm leading-6 [overflow-wrap:anywhere]",
						isCompleted && "line-through text-muted-foreground",
						isInProgress && "font-medium text-foreground",
					)}
				>
					{isInProgress ? todo.active_form : todo.content}
				</span>
			</div>
		</motion.div>
	);
}

export function TodoList({ todos, className }: TodoListProps) {
	const reducedMotion = useReducedMotion();
	// Calculate progress
	const progress = useMemo(() => {
		if (todos.length === 0) return { completed: 0, total: 0, percent: 0 };
		const completed = todos.filter((t) => t.status === "completed").length;
		return {
			completed,
			total: todos.length,
			percent: Math.round((completed / todos.length) * 100),
		};
	}, [todos]);

	if (todos.length === 0) {
		return null;
	}

	return (
		<div
			className={cn(
				"max-w-2xl overflow-hidden rounded-[var(--bf-radius-surface)] border border-border bg-card shadow-sm",
				className,
			)}
		>
			{/* Header with progress */}
			<div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 bg-muted/30 px-4 py-3">
				<div className="flex items-center gap-2">
					<ListTodo className="h-4 w-4 text-muted-foreground" />
					<span className="text-sm font-medium leading-5">
						Task Progress
					</span>
				</div>
				<div className="flex items-center gap-2">
					<span className="text-xs leading-5 text-muted-foreground">
						{progress.completed}/{progress.total}
					</span>
					{/* Progress bar */}
					<div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
						<motion.div
							className="h-full rounded-full bg-[var(--bf-info)]"
							initial={reducedMotion ? false : { width: 0 }}
							animate={{ width: `${progress.percent}%` }}
							transition={{ duration: reducedMotion ? 0 : 0.3 }}
						/>
					</div>
				</div>
			</div>

			{/* Todo items */}
			<div className="max-h-64 space-y-1 overflow-y-auto p-2">
				<AnimatePresence mode="popLayout">
					{todos.map((todo, index) => (
						<TodoItemRow
							key={`${todo.content}-${index}`}
							todo={todo}
							index={index}
						/>
					))}
				</AnimatePresence>
			</div>
		</div>
	);
}
