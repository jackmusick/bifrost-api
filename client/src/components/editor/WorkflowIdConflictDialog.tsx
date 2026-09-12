import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import type { components } from "@/lib/v1";

type WorkflowIdConflict = components["schemas"]["WorkflowIdConflict"];

interface WorkflowIdConflictDialogProps {
	conflicts: WorkflowIdConflict[];
	open: boolean;
	onUseExisting: () => void;
	onGenerateNew: () => void;
	onCancel: () => void;
}

/**
 * Dialog shown when uploading/saving a workflow file that would overwrite
 * existing workflows and lose their IDs.
 *
 * Gives the user the choice to:
 * 1. Use the existing IDs from the database (preserves workflow continuity)
 * 2. Generate new IDs (creates new workflow entries, orphans old ones)
 * 3. Cancel the operation
 */
export function WorkflowIdConflictDialog({
	conflicts,
	open,
	onUseExisting,
	onGenerateNew,
	onCancel,
}: WorkflowIdConflictDialogProps) {
	return (
		<Dialog open={open} onOpenChange={(open) => !open && onCancel()}>
			<DialogContent className="z-[100] sm:max-w-[600px]">
				<DialogHeader>
					<DialogTitle className="flex items-start gap-2">
						<AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--bf-warning)]" />
						Workflow ID conflict
					</DialogTitle>
					<DialogDescription>
						{conflicts.length === 1
							? "This file contains a workflow that already exists in the database but the file doesn't have an ID in the decorator."
							: `This file contains ${conflicts.length} workflows that already exist in the database but don't have IDs in their decorators.`}
					</DialogDescription>
				</DialogHeader>

				<WorkflowConflictList conflicts={conflicts} />

				<div className="text-sm text-muted-foreground space-y-2 border-t pt-4">
					<p>
						<strong>Use Existing IDs:</strong> The existing workflow
						IDs will be injected into the file. This preserves
						execution history, schedules, and any references to
						these workflows.
					</p>
					<p>
						<strong>Generate New IDs:</strong> New UUIDs will be
						created. The old workflow entries will become orphaned
						and their history may be lost.
					</p>
				</div>

				<DialogFooter className="flex flex-wrap gap-2">
					<Button
						type="button"
						className="min-h-11 h-auto whitespace-normal"
						variant="outline"
						onClick={onCancel}
					>
						Cancel
					</Button>
					<Button
						type="button"
						className="min-h-11 h-auto whitespace-normal"
						variant="destructive"
						onClick={onGenerateNew}
					>
						Generate New IDs
					</Button>
					<Button
						type="button"
						className="min-h-11 h-auto whitespace-normal"
						onClick={onUseExisting}
					>
						Use Existing IDs
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

function WorkflowConflictList({
	conflicts,
}: {
	conflicts: WorkflowIdConflict[];
}) {
	return (
		<ul
			aria-label="Workflows with conflicting IDs"
			tabIndex={0}
			className="min-w-0 max-h-64 overflow-y-auto divide-y rounded-[var(--bf-radius-surface)] border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
		>
			{conflicts.map((conflict) => (
				<li
					key={conflict.function_name}
					className="min-w-0 space-y-3 p-3 [overflow-wrap:anywhere]"
				>
					<p className="text-sm font-medium">{conflict.name}</p>
					<dl className="grid min-w-0 gap-3 text-sm sm:grid-cols-2">
						<div className="min-w-0">
							<dt className="text-muted-foreground">Function</dt>
							<dd className="mt-1 font-mono">
								{conflict.function_name}
							</dd>
						</div>
						<div className="min-w-0">
							<dt className="text-muted-foreground">
								Existing ID
							</dt>
							<dd className="mt-1 font-mono">
								{conflict.existing_id}
							</dd>
						</div>
					</dl>
				</li>
			))}
		</ul>
	);
}
