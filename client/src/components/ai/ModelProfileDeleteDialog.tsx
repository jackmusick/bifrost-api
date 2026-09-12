import type { RefObject } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import type { AIModelProfile } from "@/services/aiModels";

export function ModelProfileDeleteDialog({ profile, pending, failed, completed = false, returnFocusRef, onClose, onConfirm }: {
	profile: AIModelProfile | null;
	returnFocusRef?: RefObject<HTMLElement | null>;
	completed?: boolean;
	pending: boolean;
	failed: boolean;
	onClose: () => void;
	onConfirm: () => void;
}) {
	const hasAgents = (profile?.referenced_agent_count ?? 0) > 0;
	const hasAssignments = (profile?.assignment_keys?.length ?? 0) > 0;
	const dialogFocus = useDialogReturnFocus(returnFocusRef, completed);
	return <AlertDialog open={Boolean(profile)} onOpenChange={(open) => { if (!open && !pending) onClose(); }}>
		<AlertDialogContent {...dialogFocus}>
			<AlertDialogHeader>
				<AlertDialogTitle>Delete model profile?</AlertDialogTitle>
				<AlertDialogDescription className="[overflow-wrap:anywhere]">{profile?.name} will be removed. Profiles used by assignments or agents must be reassigned before deletion.</AlertDialogDescription>
			</AlertDialogHeader>
			{hasAssignments && <p className="text-sm text-muted-foreground">This profile has active assignments. Reassign them to another profile first.</p>}
			{hasAgents && <p className="text-sm text-muted-foreground">This profile is used by {profile?.referenced_agent_count} {profile?.referenced_agent_count === 1 ? "agent" : "agents"}. Choose another profile for those agents first.</p>}
			{failed && <p role="alert" className="text-sm text-destructive">Could not delete this profile. Check its assignments and agent dependencies, or try again.</p>}
			<AlertDialogFooter>
				<AlertDialogCancel className="min-h-11" disabled={pending}>Cancel</AlertDialogCancel>
				<AlertDialogAction className="min-h-11 bg-destructive text-white hover:bg-destructive/90" disabled={pending || hasAssignments || hasAgents} onClick={(event) => { event.preventDefault(); onConfirm(); }}>{pending ? "Deleting…" : "Delete profile"}</AlertDialogAction>
			</AlertDialogFooter>
		</AlertDialogContent>
	</AlertDialog>;
}
