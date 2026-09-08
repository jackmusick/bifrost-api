import { type RefObject, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
	AlertDialog,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import type { AIModelPricingListItem } from "@/services/ai-pricing";

export function PricingDeleteDialog({
	pricing,
	pending,
	failed,
	completed = false,
	returnFocusRef,
	onClose,
	onConfirm,
}: {
	pricing: AIModelPricingListItem | null;
	returnFocusRef?: RefObject<HTMLElement | null>;
	completed?: boolean;
	pending: boolean;
	failed: boolean;
	onClose: () => void;
	onConfirm: () => void;
}) {
	const errorRef = useRef<HTMLDivElement>(null);
	const dialogFocus = useDialogReturnFocus(returnFocusRef, completed);
	const open = Boolean(pricing);

	useEffect(() => {
		if (!open || !failed) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [failed, open]);

	return (
		<AlertDialog
			open={open}
			onOpenChange={(nextOpen) => {
				if (pending && !nextOpen) return;
				if (!nextOpen) onClose();
			}}
		>
			<AlertDialogContent
				{...dialogFocus}
				className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0"
				onOpenAutoFocus={(event) => {
					dialogFocus.onOpenAutoFocus();
					if (failed) {
						event.preventDefault();
						errorRef.current?.focus();
						errorRef.current?.scrollIntoView({ block: "nearest" });
					}
				}}
				onEscapeKeyDown={(event) => {
					if (pending) event.preventDefault();
				}}
			>
				<AlertDialogHeader className="shrink-0 px-6 pt-6">
					<AlertDialogTitle>Delete model pricing?</AlertDialogTitle>
					<AlertDialogDescription className="[overflow-wrap:anywhere]">
						The saved rates for {pricing?.model} ({pricing?.provider})
						will be removed.
					</AlertDialogDescription>
				</AlertDialogHeader>

				<div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
					{failed && (
						<div
							ref={errorRef}
							role="alert"
							tabIndex={-1}
							className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 outline-none"
						>
							<p className="text-sm font-medium text-destructive">
								Could not remove this pricing
							</p>
							<p className="mt-1 text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
								Try again.
							</p>
						</div>
					)}
				</div>

				<AlertDialogFooter className="shrink-0 border-t border-border/70 px-6 py-4">
					<Button
						type="button"
						variant="outline"
						className="w-full sm:w-auto"
						disabled={pending}
						onClick={() => onClose()}
					>
						Cancel
					</Button>
					<Button
						type="button"
						variant="destructive"
						className="w-full sm:w-auto"
						disabled={pending}
						onClick={(event) => {
							event.preventDefault();
							onConfirm();
						}}
					>
						{pending ? "Deleting…" : "Delete pricing"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
