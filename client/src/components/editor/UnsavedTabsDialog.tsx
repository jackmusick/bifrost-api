import { UnsavedFileList } from "./UnsavedFileList";
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

interface UnsavedTabsDialogProps {
	open: boolean;
	isSaving?: boolean;
	paths: string[];
	onOpenChange: (open: boolean) => void;
	onDiscard: () => void;
	onReturnFocus: () => void;
}

export function UnsavedTabsDialog({
	open,
	isSaving = false,
	paths,
	onOpenChange,
	onDiscard,
	onReturnFocus,
}: UnsavedTabsDialogProps) {
	return (
		<AlertDialog open={open} onOpenChange={onOpenChange}>
			<AlertDialogContent
				onCloseAutoFocus={(event) => {
					event.preventDefault();
					onReturnFocus();
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>
						{paths.length
							? "Close files with unsaved changes?"
							: "Close selected tabs?"}
					</AlertDialogTitle>
					<AlertDialogDescription>
						{isSaving
							? "A file is being saved. Wait for the save to finish before closing these tabs."
							: paths.length
								? "Your changes in these files haven’t been saved. Keep editing to save them, or discard the changes and close the selected tabs."
								: "The changes have been saved. You can close the selected tabs."}
					</AlertDialogDescription>
				</AlertDialogHeader>
				{paths.length > 0 && <UnsavedFileList paths={paths} />}
				<AlertDialogFooter>
					<AlertDialogCancel className="min-h-11 h-auto whitespace-normal">
						Keep editing
					</AlertDialogCancel>
					<AlertDialogAction
						className="min-h-11 h-auto whitespace-normal bg-destructive text-destructive-foreground hover:bg-destructive/90"
						disabled={isSaving}
						onClick={onDiscard}
					>
						{isSaving
							? "Saving…"
							: paths.length
								? "Discard changes and close"
								: "Close tabs"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
