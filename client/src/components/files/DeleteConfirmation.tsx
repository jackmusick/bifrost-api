import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	AlertDialog,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { files } from "@/lib/app-sdk/files";
import { deleteFilePolicy, type FilePolicy } from "@/services/filePolicies";

export type FileDeleteTarget =
	| { kind: "file"; location: string; scope: string | null; path: string }
	| { kind: "policy"; policy: FilePolicy };

interface DeleteConfirmationProps {
	target: FileDeleteTarget;
	onClose: () => void;
	onDeleted: (target: FileDeleteTarget) => void;
	onRestoreFocus: () => void;
}

export function DeleteConfirmation({
	target,
	onClose,
	onDeleted,
	onRestoreFocus,
}: DeleteConfirmationProps) {
	const pending = useRef(false);
	const deleted = useRef(false);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState(false);
	const location =
		target.kind === "file" ? target.location : target.policy.location;
	const path = target.kind === "file" ? target.path : target.policy.path;
	const scope =
		target.kind === "file" ? target.scope : target.policy.organizationId;
	const label = target.kind === "file" ? "file" : "policy";
	async function confirm() {
		if (pending.current) return;
		pending.current = true;
		setSaving(true);
		setError(false);
		try {
			if (target.kind === "file")
				await files.delete(target.path, {
					location: target.location,
					scope: target.scope,
				});
			else await deleteFilePolicy(target.policy);
			deleted.current = true;
			onDeleted(target);
			onClose();
		} catch {
			setError(true);
		} finally {
			pending.current = false;
			setSaving(false);
		}
	}
	return (
		<AlertDialog
			open
			onOpenChange={(open) => {
				if (!open && !pending.current) onClose();
			}}
		>
			<AlertDialogContent
				className="flex flex-col gap-0 overflow-hidden p-0"
				onEscapeKeyDown={(event) => {
					if (pending.current) event.preventDefault();
				}}
				onCloseAutoFocus={(event) => {
					if (deleted.current) {
						event.preventDefault();
						onRestoreFocus();
					} else {
						// Context-menu items may unmount before focus restoration.
						setTimeout(() => {
							if (document.activeElement === document.body)
								onRestoreFocus();
						}, 0);
					}
				}}
			>
				<AlertDialogHeader className="shrink-0 border-b p-5">
					<AlertDialogTitle>Delete {label}?</AlertDialogTitle>
					<AlertDialogDescription>
						{target.kind === "file"
							? "This permanently deletes the file."
							: "Removing this policy changes which rules govern this path. Files will remain."}
					</AlertDialogDescription>
				</AlertDialogHeader>
				<div className="min-h-0 space-y-3 overflow-y-auto p-5 text-sm">
					<dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-2">
						<dt className="text-muted-foreground">Share</dt>
						<dd className="[overflow-wrap:anywhere]">{location}</dd>
						<dt className="text-muted-foreground">Path</dt>
						<dd className="font-mono text-xs [overflow-wrap:anywhere]">
							{path || "Share root"}
						</dd>
						<dt className="text-muted-foreground">Scope</dt>
						<dd className="[overflow-wrap:anywhere]">
							{!scope || scope === "global" ? "Global" : scope}
						</dd>
					</dl>
					{error && (
						<p role="alert" className="text-destructive">
							Couldn’t delete this {label}. Try again.
						</p>
					)}
					{saving && (
						<p role="status" className="text-muted-foreground">
							Deleting {label}…
						</p>
					)}
				</div>
				<AlertDialogFooter className="shrink-0 border-t p-4">
					<AlertDialogCancel disabled={saving} className="min-h-11">
						Cancel
					</AlertDialogCancel>
					<Button
						variant="destructive"
						className="min-h-11"
						disabled={saving}
						onClick={() => void confirm()}
					>
						{saving
							? "Deleting…"
							: error
								? "Retry delete"
								: `Delete ${label}`}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
