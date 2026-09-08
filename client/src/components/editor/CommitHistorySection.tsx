import { useId, useState } from "react";
import { ChevronDown, History, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { CommitInfo } from "@/hooks/useGitHub";

interface CommitHistorySectionProps {
	commits: CommitInfo[];
	totalCommits?: number;
	hasMore?: boolean;
	isLoading?: boolean;
	hasError?: boolean;
	onRetry: () => void;
}

export function CommitHistorySection({
	commits,
	totalCommits,
	hasMore,
	isLoading,
	hasError,
	onRetry,
}: CommitHistorySectionProps) {
	const [expanded, setExpanded] = useState(true);
	const id = useId();
	return (
		<section
			aria-label="Commit history"
			className={cn(
				"flex min-h-0 min-w-0 flex-col border-t",
				expanded && "flex-1",
			)}
		>
			<button
				type="button"
				aria-expanded={expanded}
				aria-controls={id}
				onClick={() => setExpanded(!expanded)}
				className="flex min-h-11 w-full shrink-0 items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring motion-reduce:transition-none"
			>
				<ChevronDown
					className={cn(
						"size-4 shrink-0 transition-transform motion-reduce:transition-none",
						!expanded && "-rotate-90",
					)}
				/>
				<History className="size-4 shrink-0" />
				<span className="min-w-0 flex-1 text-sm font-medium">
					Commits
				</span>
				<span className="text-xs tabular-nums text-muted-foreground">
					{totalCommits ?? commits.length}
				</span>
			</button>
			<div
				id={id}
				hidden={!expanded}
				className="min-h-0 flex-1 overflow-y-auto"
			>
				{isLoading && (
					<p
						role="status"
						className="flex items-center gap-2 p-3 text-sm text-muted-foreground"
					>
						<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
						Loading commits…
					</p>
				)}
				{hasError && (
					<div className="space-y-2 p-3">
						<p role="alert" className="text-sm text-destructive">
							Couldn’t load commit history.
						</p>
						<Button
							variant="outline"
							className="min-h-11"
							disabled={isLoading}
							onClick={onRetry}
						>
							Retry loading commits
						</Button>
					</div>
				)}
				{!isLoading && !hasError && commits.length === 0 && (
					<p className="p-3 text-sm text-muted-foreground">
						No commits yet.
					</p>
				)}
				{commits.length > 0 && (
					<ol className="divide-y">
						{commits.map((commit) => (
							<CommitRecord key={commit.sha} commit={commit} />
						))}
					</ol>
				)}
				{hasMore && (
					<p className="p-3 text-xs text-muted-foreground">
						Showing the latest {commits.length}
						{totalCommits !== undefined
							? ` of ${totalCommits}`
							: ""}{" "}
						commits.
					</p>
				)}
			</div>
		</section>
	);
}

function CommitRecord({ commit }: { commit: CommitInfo }) {
	const date = new Date(commit.timestamp);
	const validDate = !Number.isNaN(date.getTime());
	return (
		<li className="space-y-2 p-3 [overflow-wrap:anywhere]">
			<p className="whitespace-pre-wrap text-sm font-medium">
				{commit.message}
			</p>
			<div className="flex flex-wrap items-center gap-2">
				<Badge variant="secondary" className="h-auto">
					{commit.is_pushed ? "Pushed" : "Local commit"}
				</Badge>
				<code
					className="text-xs text-muted-foreground"
					title={commit.sha}
				>
					{commit.sha.slice(0, 7)}
				</code>
			</div>
			<p className="text-xs text-muted-foreground">{commit.author}</p>
			{validDate ? (
				<time
					dateTime={commit.timestamp}
					className="block text-xs text-muted-foreground"
				>
					{date.toLocaleString()}
				</time>
			) : (
				<p className="text-xs text-muted-foreground">
					Time unavailable
				</p>
			)}
		</li>
	);
}
