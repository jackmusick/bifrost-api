import { useEffect, useRef, useState, type RefObject } from "react";
import {
	AlertDialog,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/api-error";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";

export function ClaimDeleteDialog({
	name,
	onConfirm,
	onOpenChange,
	returnFocusRef,
}: {
	name: string;
	onConfirm: () => Promise<void>;
	onOpenChange: (open: boolean) => void;
	returnFocusRef?: RefObject<HTMLElement | null>;
}) {
	const busy = useRef(false);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const errorRef = useRef<HTMLDivElement>(null);
	const returnFocus = useDialogReturnFocus(returnFocusRef, true);
	useEffect(() => {
		if (error) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [error]);
	async function confirm() {
		if (busy.current) return;
		busy.current = true;
		setPending(true);
		setError(null);
		try {
			await onConfirm();
		} catch (cause) {
			setError(
				getErrorMessage(
					cause,
					"The request could not be completed. Try again.",
				),
			);
		} finally {
			busy.current = false;
			setPending(false);
		}
	}
	return (
		<AlertDialog
			open
			onOpenChange={(open) => {
				if (!busy.current) onOpenChange(open);
			}}
		>
			<AlertDialogContent
				{...returnFocus}
				className="max-h-[90dvh] overflow-y-auto"
				onEscapeKeyDown={(event) => {
					if (busy.current) event.preventDefault();
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>Delete custom claim</AlertDialogTitle>
					<AlertDialogDescription className="[overflow-wrap:anywhere]">
						Delete “{name}”? Any table policy referencing this claim
						will be rejected at save time until you remove the
						reference. This cannot be undone.
					</AlertDialogDescription>
				</AlertDialogHeader>
				{error && (
					<div
						ref={errorRef}
						role="alert"
						tabIndex={-1}
						className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 text-sm outline-none [overflow-wrap:anywhere]"
					>
						<p className="font-medium text-destructive">
							Claim could not be deleted
						</p>
						<p className="mt-1 text-muted-foreground">{error}</p>
					</div>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel disabled={pending} className="min-h-11">
						Cancel
					</AlertDialogCancel>
					<Button
						variant="destructive"
						disabled={pending}
						className="min-h-11"
						onClick={() => void confirm()}
					>
						{pending ? "Deleting…" : "Delete"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
