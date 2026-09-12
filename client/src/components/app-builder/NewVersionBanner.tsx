/**
 * New Version Banner
 *
 * Shows a persistent indicator when a new version has been published:
 * - "New version available" with refresh button
 * - Calls onRefresh to do a soft refresh (invalidate queries, reset store)
 */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NewVersionBannerProps {
	/** Whether a new version is available */
	isVisible: boolean;
	/** Callback to refresh the app */
	onRefresh: () => void;
}

/**
 * Displays a banner when a new published version is available
 *
 * @example
 * <NewVersionBanner
 *   isVisible={newVersionAvailable}
 *   onRefresh={() => refreshApp()}
 * />
 */
export function NewVersionBanner({ isVisible, onRefresh }: NewVersionBannerProps) {
	const reduceMotion = useReducedMotion();

	return (
		<AnimatePresence>
			{isVisible && (
				<motion.div
					key="new-version-banner"
					initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
					animate={reduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1 }}
					exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
					transition={{ duration: reduceMotion ? 0 : 0.15 }}
					className="flex min-h-11 flex-wrap items-center gap-2 rounded-[var(--bf-radius-control)] border border-[color:var(--bf-info-soft)] bg-[color:var(--bf-info-soft)]/20 px-3 py-2 text-sm"
					aria-live="polite"
				>
					<span className="font-medium text-[var(--bf-info)]">
						New version available
					</span>
					<Button
						variant="ghost"
						size="sm"
						className="min-h-11 px-3 text-[var(--bf-info)] hover:bg-[color:var(--bf-info-soft)]/30 hover:text-[var(--bf-info)]"
						onClick={onRefresh}
					>
						<RefreshCw className="mr-1 h-3.5 w-3.5" />
						Refresh
					</Button>
				</motion.div>
			)}
		</AnimatePresence>
	);
}

export default NewVersionBanner;
