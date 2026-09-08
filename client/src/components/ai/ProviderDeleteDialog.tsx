import type { RefObject } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import type { AIProviderConnection } from "@/services/aiModels";

export function ProviderDeleteDialog({ provider, pending, failed, completed = false, returnFocusRef, onClose, onConfirm }: {
	provider: AIProviderConnection | null;
	returnFocusRef?: RefObject<HTMLElement | null>;
	completed?: boolean;
	pending: boolean;
	failed: boolean;
	onClose: () => void;
	onConfirm: () => void;
}) {
	const hasProfiles = (provider?.profile_count ?? 0) > 0;
	const dialogFocus = useDialogReturnFocus(returnFocusRef, completed);
	return <AlertDialog open={Boolean(provider)} onOpenChange={(open) => { if (!open && !pending) onClose(); }}>
		<AlertDialogContent {...dialogFocus}>
			<AlertDialogHeader>
				<AlertDialogTitle>Delete provider connection?</AlertDialogTitle>
				<AlertDialogDescription className="[overflow-wrap:anywhere]">{provider?.name} will be removed. Connections used by model profiles or embeddings must be reassigned before deletion.</AlertDialogDescription>
			</AlertDialogHeader>
			{hasProfiles && <p className="text-sm text-muted-foreground">This connection is used by {provider?.profile_count} {provider?.profile_count === 1 ? "profile" : "profiles"}. Move or remove those profiles first.</p>}
			{failed && <p role="alert" className="text-sm text-destructive">Could not delete this connection. Check its profile and embedding dependencies, or try again.</p>}
			<AlertDialogFooter>
				<AlertDialogCancel className="min-h-11" disabled={pending}>Cancel</AlertDialogCancel>
				<AlertDialogAction className="min-h-11 bg-destructive text-white hover:bg-destructive/90" disabled={pending || hasProfiles} onClick={(event) => { event.preventDefault(); onConfirm(); }}>{pending ? "Deleting…" : "Delete connection"}</AlertDialogAction>
			</AlertDialogFooter>
		</AlertDialogContent>
	</AlertDialog>;
}
