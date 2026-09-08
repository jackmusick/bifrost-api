import { useEffect, useRef, useState, type RefObject } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
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

export function DocumentDeleteDialog({
	id,
	onClose,
	onDelete,
	returnFocusRef,
}: {
	id: string;
	onClose: () => void;
	onDelete: () => Promise<unknown>;
	returnFocusRef?: RefObject<HTMLElement | null>;
}) {
	const returnFocus = useDialogReturnFocus(returnFocusRef, true);
	const pendingRef = useRef(false);
	const [pending, setPending] = useState(false);
	const [failed, setFailed] = useState(false);
	const errorRef = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		if (failed) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [failed]);
	async function remove() {
		if (pendingRef.current) return;
		pendingRef.current = true;
		setPending(true);
		setFailed(false);
		try {
			await onDelete();
			onClose();
		} catch {
			setFailed(true);
		} finally {
			pendingRef.current = false;
			setPending(false);
		}
	}
	return (
		<AlertDialog
			open
			onOpenChange={(open) => {
				if (!open && !pendingRef.current) onClose();
			}}
		>
			<AlertDialogContent
				{...returnFocus}
				className="max-h-[90dvh] overflow-y-auto p-[var(--bf-surface-pad)]"
				onEscapeKeyDown={(event) => {
					if (pendingRef.current) event.preventDefault();
				}}
				aria-busy={pending}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>Delete document?</AlertDialogTitle>
					<AlertDialogDescription>
						This permanently removes the document from this table.
						This action cannot be undone.
					</AlertDialogDescription>
				</AlertDialogHeader>
				<p className="break-all font-mono text-xs text-muted-foreground">
					{id}
				</p>
				{failed && (
					<p
						ref={errorRef}
						tabIndex={-1}
						role="alert"
						className="text-sm text-destructive outline-none"
					>
						Document could not be deleted. Try again.
					</p>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel
						disabled={pending}
						className="min-h-11 lg:min-h-11"
					>
						Cancel
					</AlertDialogCancel>
					<Button
						type="button"
						variant="destructive"
						className="min-h-11"
						disabled={pending}
						onClick={() => void remove()}
					>
						{pending
							? "Deleting…"
							: failed
								? "Retry deletion"
								: "Delete document"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
