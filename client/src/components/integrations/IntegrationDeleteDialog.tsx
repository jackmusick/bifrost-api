import { useRef, useState, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/** Retain the selected integration resource until its deletion succeeds. */
export function IntegrationDeleteDialog({
	open,
	onOpenChange,
	title,
	children,
	onConfirm,
}: {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	title: string;
	children: ReactNode;
	onConfirm: () => Promise<void>;
}) {
	const [pending, setPending] = useState(false);
	const [error, setError] = useState(false);
	const pendingRef = useRef(false);
	const changeOpen = (next: boolean) => {
		if (pendingRef.current) return;
		setError(false);
		onOpenChange(next);
	};
	const confirm = async () => {
		if (pendingRef.current) return;
		pendingRef.current = true;
		setPending(true);
		setError(false);
		try {
			await onConfirm();
			onOpenChange(false);
		} catch {
			setError(true);
		} finally {
			pendingRef.current = false;
			setPending(false);
		}
	};
	return (
		<AlertDialog open={open} onOpenChange={changeOpen}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>{title}</AlertDialogTitle>
					<AlertDialogDescription>{children}</AlertDialogDescription>
				</AlertDialogHeader>
				{error && (
					<Alert variant="destructive">
						<AlertDescription>
							Could not delete. Try again.
						</AlertDescription>
					</Alert>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel disabled={pending}>
						Cancel
					</AlertDialogCancel>
					<AlertDialogAction
						variant="destructive"
						disabled={pending}
						onClick={(event) => {
							event.preventDefault();
							void confirm();
						}}
					>
						{pending && (
							<Loader2
								aria-hidden="true"
								className="size-4 motion-safe:animate-spin"
							/>
						)}
						{pending ? "Deleting…" : "Delete"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
