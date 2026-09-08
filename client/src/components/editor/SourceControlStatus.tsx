import { GitBranch, Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SourceControlHeader({
	branch,
	isFetching,
	disabled,
	onFetch,
}: {
	branch?: string | null | undefined;
	isFetching: boolean;
	disabled: boolean;
	onFetch: () => void;
}) {
	return (
		<header className="flex shrink-0 items-start gap-2 border-b p-3">
			<GitBranch className="mt-1 size-4 shrink-0 text-muted-foreground" />
			<div className="min-w-0 flex-1 space-y-1">
				<h3 className="text-sm font-semibold">Source control</h3>
				{branch && (
					<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
						{branch}
					</p>
				)}
			</div>
			<Button
				type="button"
				variant="ghost"
				size="icon"
				className="size-11 shrink-0"
				aria-label="Fetch from remote"
				title="Fetch from remote"
				disabled={disabled}
				onClick={onFetch}
			>
				{isFetching ? (
					<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
				) : (
					<RefreshCw className="size-4" />
				)}
			</Button>
		</header>
	);
}

export function SourceControlMergeBanner({
	conflictCount,
	resolvedCount,
	disabled,
	onAbortMerge,
}: {
	conflictCount: number;
	resolvedCount: number;
	disabled: boolean;
	onAbortMerge: () => void;
}) {
	const remaining = Math.max(0, conflictCount - resolvedCount);
	return (
		<section aria-label="Merge status" className="space-y-3 border-b p-3">
			<p role="status" className="flex items-start gap-2 text-sm">
				<AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--bf-warning)]" />
				<span>
					{remaining > 0
						? `${remaining} conflict${remaining === 1 ? "" : "s"} remaining`
						: "All conflict versions selected"}
				</span>
			</p>
			<p className="text-xs text-muted-foreground">
				{remaining > 0
					? "Review each conflict and choose which version to keep."
					: "Complete the merge to apply your selections."}
			</p>
			<Button
				type="button"
				variant="outline"
				className="min-h-11 h-auto whitespace-normal"
				disabled={disabled}
				onClick={onAbortMerge}
			>
				Abort merge
			</Button>
		</section>
	);
}
