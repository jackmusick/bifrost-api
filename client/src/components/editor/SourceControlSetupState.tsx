import { GitBranch, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SourceControlSetupState({
	state,
	busy = false,
	onAction,
}: {
	state: "loading" | "error" | "configure" | "initialize";
	busy?: boolean;
	onAction?: () => void;
}) {
	return (
		<section
			aria-label="Source control"
			className="flex h-full min-h-0 min-w-0 flex-col overflow-y-auto p-3"
		>
			<h3 className="flex items-center gap-2 text-sm font-semibold">
				<GitBranch className="size-4 shrink-0" />
				Source control
			</h3>
			<div className="my-auto space-y-3 py-6">
				{state === "loading" ? (
					<p
						role="status"
						className="flex items-center gap-2 text-sm text-muted-foreground"
					>
						<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
						Loading Git status…
					</p>
				) : state === "error" ? (
					<>
						<p role="alert" className="text-sm text-destructive">
							Couldn’t load Git status.
						</p>
						<p className="text-sm text-muted-foreground">
							Try again to check your repository connection.
						</p>
						<Button
							type="button"
							variant="outline"
							className="min-h-11 h-auto whitespace-normal"
							onClick={onAction}
							disabled={busy}
						>
							{busy ? "Retrying…" : "Retry Git status"}
						</Button>
					</>
				) : state === "initialize" ? (
					<>
						<h4 className="text-sm font-medium">
							GitHub connected
						</h4>
						<p className="text-sm text-muted-foreground">
							Fetch your repository to start reviewing changes.
						</p>
						<Button
							type="button"
							className="min-h-11 h-auto whitespace-normal"
							onClick={onAction}
							disabled={busy}
						>
							{busy && (
								<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
							)}
							{busy ? "Fetching…" : "Fetch from GitHub"}
						</Button>
					</>
				) : (
					<>
						<h4 className="text-sm font-medium">
							Connect your repository
						</h4>
						<p className="text-sm text-muted-foreground">
							Configure GitHub in Settings to use source control.
						</p>
					</>
				)}
			</div>
		</section>
	);
}
