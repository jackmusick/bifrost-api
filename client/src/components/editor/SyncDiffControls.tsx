import { AlertTriangle, FileCode, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DiffPreviewState } from "@/stores/editorStore";

export function SyncDiffHeader({
	preview,
	onClose,
}: {
	preview: DiffPreviewState;
	onClose: () => void;
}) {
	const conflictLabel =
		preview.conflictType === "deleted_by_us"
			? "Deleted locally, modified on remote"
			: preview.conflictType === "deleted_by_them"
				? "Modified locally, deleted on remote"
				: preview.conflictType === "both_added"
					? "Added on both sides with different content"
					: null;
	return (
		<header className="shrink-0 border-b p-3 space-y-3">
			<div className="flex items-start gap-2">
				<FileCode className="mt-1 size-4 shrink-0 text-muted-foreground" />
				<div className="min-w-0 flex-1">
					<h3 className="text-sm font-semibold [overflow-wrap:anywhere]">
						{preview.displayName}
					</h3>
					<p className="font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
						{preview.path}
					</p>
				</div>
				<Button
					type="button"
					variant="ghost"
					size="icon"
					className="size-11 shrink-0"
					aria-label="Close diff view"
					onClick={onClose}
				>
					<X className="size-4" />
				</Button>
			</div>
			{preview.isConflict && conflictLabel && (
				<p className="flex items-start gap-2 text-sm">
					<AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--bf-warning)]" />
					<span>{conflictLabel}</span>
				</p>
			)}
		</header>
	);
}

export function SyncDiffResolution({ preview }: { preview: DiffPreviewState }) {
	if (!preview.isConflict || !preview.onResolve) return null;
	const localLabel =
		preview.conflictType === "deleted_by_us"
			? "Keep local deletion"
			: "Keep local";
	const remoteLabel =
		preview.conflictType === "deleted_by_them"
			? "Keep remote deletion"
			: "Keep remote";
	return (
		<footer className="shrink-0 space-y-2 border-t p-3">
			<p className="text-xs text-muted-foreground">
				Choose a version, then complete the merge in Source control.
			</p>
			<div className="flex flex-wrap gap-2">
				{(
					[
						["ours", localLabel],
						["theirs", remoteLabel],
					] as const
				).map(([value, label]) => (
					<Button
						key={value}
						type="button"
						variant={
							preview.resolution === value
								? "secondary"
								: "outline"
						}
						aria-pressed={preview.resolution === value}
						className="min-h-11 h-auto whitespace-normal"
						onClick={() => preview.onResolve?.(value)}
					>
						{label}
					</Button>
				))}
			</div>
		</footer>
	);
}
