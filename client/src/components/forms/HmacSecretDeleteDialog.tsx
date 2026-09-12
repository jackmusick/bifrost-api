import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

export function HmacSecretDeleteDialog({ name, pending, error, onClose, onConfirm }: { name: string | null; pending: boolean; error: boolean; onClose: () => void; onConfirm: () => void }) {
	return (
		<AlertDialog open={name !== null} onOpenChange={open => { if (!open && !pending) onClose(); }}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Delete embed secret?</AlertDialogTitle>
					<AlertDialogDescription className="[overflow-wrap:anywhere]">This will permanently delete “{name}”. Any integrations using this secret will stop working.</AlertDialogDescription>
				</AlertDialogHeader>
				{error && <p role="alert" className="text-sm text-destructive">Could not delete the secret. Try again.</p>}
				{pending && <p role="status" className="text-sm text-muted-foreground">Deleting secret…</p>}
				<AlertDialogFooter>
					<AlertDialogCancel className="min-h-11 lg:min-h-11" disabled={pending}>Cancel</AlertDialogCancel>
					<Button type="button" variant="destructive" className="min-h-11 lg:min-h-11" disabled={pending} onClick={onConfirm}>{pending ? "Deleting…" : error ? "Retry deletion" : "Delete"}</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
