import type { ChangedFile } from "@/hooks/useGitHub";
import { SourceOperationDialog } from "./SourceOperationDialog";

/** Mounted for one confirmation, so the reviewed file set stays fixed during refreshes. */
export function SourceDiscardDialog({
	files,
	onClose,
	onConfirm,
	unavailableReason,
}: {
	files: ChangedFile[];
	unavailableReason?: string | undefined;
	onClose: () => void;
	onConfirm: (files: ChangedFile[]) => Promise<void>;
}) {
	return (
		<SourceOperationDialog
			unavailableReason={unavailableReason}
			title="Discard changes?"
			description={`${files.length === 1 ? "Discard uncommitted changes to this file." : `Discard uncommitted changes to these ${files.length} files.`} This cannot be undone.`}
			confirmLabel="Discard changes"
			pendingLabel="Discarding changes…"
			cancelLabel="Keep changes"
			onClose={onClose}
			onConfirm={() => onConfirm(files)}
		>
			<ul
				aria-label="Files to discard"
				tabIndex={0}
				className="max-h-64 space-y-2 overflow-y-auto rounded-[var(--bf-radius-surface)] border p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				{files.map((file) => (
					<li key={file.path} className="min-w-0">
						<code className="text-sm leading-5 [overflow-wrap:anywhere]">{file.path}</code>
					</li>
				))}
			</ul>
		</SourceOperationDialog>
	);
}
