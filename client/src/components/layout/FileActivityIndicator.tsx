import { useMemo, useState, useEffect, useId } from "react";
import { Radio } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useFileActivityStore } from "@/stores/fileActivityStore";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function FileActivityIndicator() {
	const { user } = useAuth();
	const titleId = useId();
	const activeWatchers = useFileActivityStore((s) => s.activeWatchers);
	const recentPushes = useFileActivityStore((s) => s.recentPushes);

	// Tick every 15s to re-evaluate recency filtering
	const [now, setNow] = useState(() => Date.now());
	useEffect(() => {
		const timer = setInterval(() => setNow(Date.now()), 15_000);
		return () => clearInterval(timer);
	}, []);

	// Show all watchers (including own — confirms your watch session is live)
	// Filter out own pushes to avoid echo noise
	const recentOtherPushes = useMemo(
		() =>
			recentPushes.filter(
				(p) =>
					p.user_id !== user?.id &&
					now - new Date(p.timestamp).getTime() < 60_000,
			),
		[recentPushes, user?.id, now],
	);

	if (activeWatchers.length === 0 && recentOtherPushes.length === 0)
		return null;

	const hasLiveWatcher = activeWatchers.length > 0;

	const label = hasLiveWatcher
		? activeWatchers.length > 1
			? `${activeWatchers.length} developers active`
			: `${activeWatchers[0].user_name} editing ${activeWatchers[0].prefix}`
		: recentOtherPushes.length > 0
			? `${recentOtherPushes[recentOtherPushes.length - 1].user_name} pushed files`
			: "";

	return (
		<Popover>
			<PopoverTrigger asChild>
				<Button
					type="button"
					variant="ghost"
					aria-label={`File activity: ${label}`}
					className="min-h-11 min-w-11 max-w-60 gap-2 text-muted-foreground"
				>
					<Radio
						className={cn(
							"h-4 w-4 shrink-0",
							hasLiveWatcher
								? "text-[var(--bf-success)] motion-safe:animate-pulse"
								: "text-[var(--bf-info)]",
						)}
					/>
					<span className="hidden min-w-0 lg:inline max-w-48 truncate">
						{label}
					</span>
				</Button>
			</PopoverTrigger>
			<PopoverContent
				side="bottom"
				collisionPadding={16}
				sideOffset={8}
				align="end"
				aria-labelledby={titleId}
				className="max-h-[min(28rem,var(--radix-popover-content-available-height))] w-80 max-w-[calc(100vw-2rem)] overflow-y-auto [overflow-wrap:anywhere]"
			>
				<h2 id={titleId} className="font-medium">
					File activity
				</h2>
				{activeWatchers.length > 0 && (
					<div className="space-y-2">
						<p className="font-medium">Active watchers:</p>
						{activeWatchers.map((w) => (
							<p key={`${w.user_id}:${w.prefix}`}>
								<span className="block">{w.user_name}</span>
								<span className="block font-mono text-sm text-muted-foreground">
									{w.prefix}
								</span>
							</p>
						))}
					</div>
				)}
				{recentOtherPushes.length > 0 && (
					<div className="space-y-2 border-t pt-3">
						<p className="font-medium">Recent file changes:</p>
						{recentOtherPushes.slice(-5).map((p, i) => (
							<p key={i}>
								<span className="block">
									{p.user_name} · {p.file_count} files
								</span>
								<span className="block font-mono text-sm text-muted-foreground">
									{p.prefix}
								</span>
							</p>
						))}
					</div>
				)}
			</PopoverContent>
		</Popover>
	);
}
