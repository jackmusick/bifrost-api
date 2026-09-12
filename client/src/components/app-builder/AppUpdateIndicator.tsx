/**
 * App Update Indicator
 *
 * Shows brief attribution when someone else updates the app:
 * - "[avatar] {name} updated" message (2-3 seconds, then fades)
 * - Uses the same motion shell as the other header banners
 */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface AppUpdateIndicatorProps {
	/** Info about the last update (who and when) */
	lastUpdate?: {
		userName: string;
		timestamp: Date;
	} | null;
}

/**
 * Displays brief attribution when an app is updated by another user
 *
 * @example
 * <AppUpdateIndicator
 *   lastUpdate={{ userName: "John Doe", timestamp: new Date() }}
 * />
 */
export function AppUpdateIndicator({ lastUpdate }: AppUpdateIndicatorProps) {
	const reduceMotion = useReducedMotion();
	const initials = lastUpdate
		? lastUpdate.userName
				.split(" ")
				.map((n) => n[0])
				.filter(Boolean)
				.join("")
				.toUpperCase()
				.slice(0, 2) || "?"
		: "";

	const relativeUpdatedAt = lastUpdate
		? formatRelativeTime(lastUpdate.timestamp)
		: "";

	return (
		<AnimatePresence>
			{lastUpdate && (
				<motion.div
					key="update-indicator"
					initial={
						reduceMotion ? { opacity: 0 } : { opacity: 0, x: 10 }
					}
					animate={
						reduceMotion ? { opacity: 1 } : { opacity: 1, x: 0 }
					}
					exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -10 }}
					transition={{ duration: reduceMotion ? 0 : 0.15 }}
					className="flex min-w-0 items-center gap-2 rounded-[var(--bf-radius-control)] border border-border/70 bg-background px-2.5 py-1.5 text-sm text-muted-foreground shadow-sm"
					aria-live="polite"
				>
					<Avatar className="h-5 w-5">
						<AvatarFallback className="text-xs bg-primary/10 text-primary">
							{initials}
						</AvatarFallback>
					</Avatar>
					<span className="min-w-0 flex-1">
						<span className="block truncate text-foreground" title={lastUpdate.userName}>{lastUpdate.userName}</span>{" "}
						updated{" "}
						<time
							dateTime={lastUpdate.timestamp.toISOString()}
							title={lastUpdate.timestamp.toLocaleString()}
							className="text-muted-foreground"
						>
							{relativeUpdatedAt}
						</time>
					</span>
				</motion.div>
			)}
		</AnimatePresence>
	);
}

function formatRelativeTime(timestamp: Date): string {
	const diffMs = timestamp.getTime() - Date.now();
	const diffMinutes = Math.round(diffMs / 60000);
	const diffHours = Math.round(diffMs / 3600000);
	const diffDays = Math.round(diffMs / 86400000);
	const absMinutes = Math.abs(diffMinutes);
	const absHours = Math.abs(diffHours);

	if (Math.abs(diffMs) < 60000) return "just now";
	if (absMinutes < 60)
		return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
			diffMinutes,
			"minute",
		);
	if (absHours < 24)
		return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
			diffHours,
			"hour",
		);
	return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
		diffDays,
		"day",
	);
}

export default AppUpdateIndicator;
