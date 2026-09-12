import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TextExecutionResult } from "./TextExecutionResult";
import { Skeleton } from "@/components/ui/skeleton";
import { PrettyInputDisplay } from "./PrettyInputDisplay";
import { SafeHTMLRenderer } from "./SafeHTMLRenderer";

interface ExecutionResultPanelProps {
	/** The execution result (can be object, string, or null) */
	result?: unknown;
	/** How to render the result: 'json', 'html', 'text', or undefined for auto-detect */
	resultType?: string | null;
	/** Workflow name for HTML title */
	workflowName?: string;
	/** Whether the result is still loading */
	isLoading?: boolean;
	/** Optional className for the section */
	className?: string;
}

export function ExecutionResultPanel({
	result,
	resultType,
	workflowName,
	isLoading = false,
	className,
}: ExecutionResultPanelProps) {
	const reduceMotion = useReducedMotion();
	const fadeTransition = reduceMotion ? { duration: 0 } : { duration: 0.2 };

	const renderResult = () => {
		// JSON result type
		if (
			resultType === "json" &&
			typeof result === "object" &&
			result !== null
		) {
			return (
				<PrettyInputDisplay
					inputData={result as Record<string, unknown> | unknown[]}
					showToggle={true}
					showDescription={false}
					defaultView="pretty"
					context="result"
				/>
			);
		}

		// HTML result type
		if (resultType === "html" && typeof result === "string") {
			return (
				<SafeHTMLRenderer
					html={result}
					title={
						workflowName
							? `${workflowName} - Execution Result`
							: "Execution Result"
					}
				/>
			);
		}

		// Text result type
		if (resultType === "text" && typeof result === "string") {
			return <TextExecutionResult value={result} />;
		}

		// Auto-detect: object without explicit type
		if (!resultType && typeof result === "object" && result !== null) {
			return (
				<PrettyInputDisplay
					inputData={result as Record<string, unknown> | unknown[]}
					showToggle={true}
					showDescription={false}
					defaultView="pretty"
					context="result"
				/>
			);
		}

		// String without explicit type
		if (!resultType && typeof result === "string") {
			return <TextExecutionResult value={result} />;
		}

		// Primitive values
		if (result !== null && result !== undefined) {
			return <TextExecutionResult value={String(result)} />;
		}

		return null;
	};

	const body = (
		<AnimatePresence mode="wait">
			{isLoading ? (
				<motion.div
					key="loading"
					role="status"
					aria-label="Loading execution result"
					initial={reduceMotion ? false : { opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={fadeTransition}
					className="space-y-3"
				>
					<Skeleton className="h-4 w-full" />
					<Skeleton className="h-4 w-3/4" />
					<Skeleton className="h-4 w-5/6" />
				</motion.div>
			) : result === null || result === undefined ? (
				<motion.div
					key="empty"
					initial={reduceMotion ? false : { opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={fadeTransition}
					className="text-center text-muted-foreground py-8"
				>
					No result returned
				</motion.div>
			) : (
				<motion.div
					key="content"
					initial={reduceMotion ? false : { opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={fadeTransition}
				>
					{renderResult()}
				</motion.div>
			)}
		</AnimatePresence>
	);

	return <section className={cn("min-w-0", className)}>{body}</section>;
}
