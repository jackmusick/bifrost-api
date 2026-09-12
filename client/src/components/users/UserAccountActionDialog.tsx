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

export function UserAccountActionDialog({
	mode,
	name,
	onOpenChange,
	onConfirm,
	returnFocusRef,
}: {
	mode: "disable" | "delete";
	name: string;
	onOpenChange: (open: boolean) => void;
	onConfirm: () => Promise<void>;
	returnFocusRef?: RefObject<HTMLElement | null>;
}) {
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const busy = useRef(false);
	const errorRef = useRef<HTMLDivElement>(null);
	const returnFocus = useDialogReturnFocus(returnFocusRef, true);
	const deleting = mode === "delete";
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
					<AlertDialogTitle>
						{deleting ? "Permanently delete user" : "Disable user"}
					</AlertDialogTitle>
					<AlertDialogDescription className="[overflow-wrap:anywhere]">
						{deleting ? (
							<>
								Permanently delete “{name}”? This cannot be
								undone. The user and their associated data will
								be removed.
							</>
						) : (
							<>
								Disable “{name}”? They will lose access to the
								platform. You can re-enable them later.
							</>
						)}
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
							{deleting
								? "User could not be deleted"
								: "User could not be disabled"}
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
						{pending
							? deleting
								? "Deleting…"
								: "Disabling…"
							: deleting
								? "Permanently delete"
								: "Disable"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
