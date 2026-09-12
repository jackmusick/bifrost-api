import { useId } from "react";
import { Loader2, RefreshCw, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SourceControlActionsProps {
	hasChanges: boolean;
	hasConflicts: boolean;
	allConflictsResolved: boolean;
	commitMessage: string;
	onCommitMessageChange: (value: string) => void;
	onCommit: () => void;
	onCompleteMerge: () => void;
	onSync: () => void;
	commitsAhead: number;
	commitsBehind: number;
	needsSync: boolean;
	disabled: boolean;
	loading: string | null;
	branch: string;
}
export function SourceControlActions(props: SourceControlActionsProps) {
	const id = useId();
	const hasRemoteChanges = props.commitsAhead > 0 || props.commitsBehind > 0;
	const syncBlocked = props.hasChanges && hasRemoteChanges;
	if (props.hasConflicts)
		return (
			<div className="space-y-2 p-3">
				<Button
					type="button"
					className="min-h-11 h-auto w-full whitespace-normal"
					disabled={props.disabled || !props.allConflictsResolved}
					onClick={props.onCompleteMerge}
				>
					{props.loading === "resolving" ? (
						<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
					) : (
						<CheckCircle2 className="size-4 shrink-0" />
					)}
					{props.loading === "resolving"
						? "Completing merge…"
						: "Complete merge"}
				</Button>
				{!props.allConflictsResolved && (
					<p className="text-xs text-muted-foreground">
						Choose a version for every conflict before completing
						the merge.
					</p>
				)}
			</div>
		);
	return (
		<div className="space-y-3 p-3">
			{props.hasChanges && (
				<form
					className="space-y-2"
					onSubmit={(event) => {
						event.preventDefault();
						if (!props.disabled && props.commitMessage.trim())
							props.onCommit();
					}}
				>
					<Label htmlFor={id}>Commit message</Label>
					<Input
						id={id}
						value={props.commitMessage}
						onChange={(event) =>
							props.onCommitMessageChange(event.target.value)
						}
						placeholder="Describe your changes"
						disabled={props.disabled}
						className="min-h-11"
					/>
					<Button
						type="submit"
						className="min-h-11 h-auto w-full whitespace-normal"
						disabled={props.disabled || !props.commitMessage.trim()}
					>
						{props.loading === "committing" && (
							<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
						)}
						{props.loading === "committing"
							? "Committing…"
							: "Commit changes"}
					</Button>
					<p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
						Commit to{" "}
						<span className="font-mono">{props.branch}</span>
					</p>
				</form>
			)}
			{(hasRemoteChanges || props.needsSync) && (
				<div className="space-y-2">
					<Button
						type="button"
						variant={props.hasChanges ? "outline" : "default"}
						className="min-h-11 h-auto w-full whitespace-normal"
						disabled={props.disabled || syncBlocked}
						onClick={props.onSync}
					>
						{props.loading === "syncing" ? (
							<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
						) : (
							<RefreshCw className="size-4 shrink-0" />
						)}
						{props.loading === "syncing"
							? "Syncing…"
							: "Sync origin"}
					</Button>
					{hasRemoteChanges && (
						<p className="text-xs text-muted-foreground">
							{props.commitsAhead} outgoing ·{" "}
							{props.commitsBehind} incoming
						</p>
					)}
					{syncBlocked && (
						<p className="text-xs text-muted-foreground">
							Commit your changes before syncing.
						</p>
					)}
				</div>
			)}
		</div>
	);
}
