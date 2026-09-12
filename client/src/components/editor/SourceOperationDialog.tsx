import { useRef, useState } from "react";
import { Loader2 } from "lucide-react";
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
import type { ReactNode } from "react";

/** Mount for one operation; the host owns its side effects and rejects failures. */
export function SourceOperationDialog({
	title,
	description,
	confirmLabel,
	pendingLabel,
	cancelLabel,
	onClose,
	onConfirm,
	children,
	unavailableReason,
	onRestoreFocus,
}: {
	title: string;
	description: string;
	confirmLabel: string;
	pendingLabel: string;
	cancelLabel: string;
	onClose: () => void;
	onConfirm: () => Promise<void>;
	children?: ReactNode;
	unavailableReason?: string | undefined;
	onRestoreFocus?: () => void;
}) {
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const submitting = useRef(false);
	const confirm = async () => {
		if (submitting.current || unavailableReason) return;
		submitting.current = true;
		setPending(true);
		setError(null);
		try {
			await onConfirm();
			onClose();
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: "Couldn’t complete this operation. Try again.",
			);
		} finally {
			submitting.current = false;
			setPending(false);
		}
	};
	return (
		<AlertDialog
			open
			onOpenChange={(open) => {
				if (!open && !submitting.current) onClose();
			}}
		>
			<AlertDialogContent
				onCloseAutoFocus={(event) => {
					if (onRestoreFocus) {
						event.preventDefault();
						onRestoreFocus();
					}
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>{title}</AlertDialogTitle>
					<AlertDialogDescription>
						{description}
					</AlertDialogDescription>
				</AlertDialogHeader>
				{children}
				{unavailableReason && !pending && (
					<p role="alert" className="text-sm leading-5 text-muted-foreground [overflow-wrap:anywhere]">
						{unavailableReason}
					</p>
				)}
				{error && (
					<p
						role="alert"
						className="text-sm leading-5 text-destructive [overflow-wrap:anywhere]"
					>
						{error}
					</p>
				)}
				{pending && (
					<p role="status" className="text-sm leading-5 text-muted-foreground [overflow-wrap:anywhere]">
						{pendingLabel}
					</p>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel disabled={pending} className="min-h-11">
						{cancelLabel}
					</AlertDialogCancel>
					<Button
						type="button"
						variant="destructive"
						disabled={pending || !!unavailableReason}
						onClick={() => void confirm()}
						className="min-h-11 h-auto whitespace-normal"
					>
						{pending && (
							<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						)}
						{pending ? pendingLabel : confirmLabel}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
