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

interface EditorCloseDialogProps {
	open: boolean;
	unsavedPaths: string[];
	isSaving: boolean;
	isUploading: boolean;
	onOpenChange: (open: boolean) => void;
	onConfirm: () => void;
	onReturnFocus: () => void;
}

export function EditorCloseDialog({
	open,
	unsavedPaths,
	isSaving,
	isUploading,
	onOpenChange,
	onConfirm,
	onReturnFocus,
}: EditorCloseDialogProps) {
	const hasUnsavedFiles = unsavedPaths.length > 0;
	return (
		<AlertDialog open={open} onOpenChange={onOpenChange}>
			<AlertDialogContent
				onCloseAutoFocus={(event) => {
					event.preventDefault();
					onReturnFocus();
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>Close editor?</AlertDialogTitle>
					<AlertDialogDescription>
						{isSaving
							? "A file is being saved. Wait for the save to finish before closing the editor."
							: hasUnsavedFiles
								? "These files have unsaved changes. Keep editing to save them, or discard the changes and close the editor."
								: "Closing the editor will close all open files."}
					</AlertDialogDescription>
				</AlertDialogHeader>
				{hasUnsavedFiles && <UnsavedFileList paths={unsavedPaths} />}
				{isUploading && (
					<p className="text-sm text-muted-foreground">
						An upload is in progress. Closing will also cancel the
						remaining uploads. Files already uploaded will remain.
					</p>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel className="min-h-11 h-auto whitespace-normal">
						Keep editing
					</AlertDialogCancel>
					<AlertDialogAction
						className="min-h-11 h-auto whitespace-normal bg-destructive text-destructive-foreground hover:bg-destructive/90"
						disabled={isSaving}
						onClick={onConfirm}
					>
						{isSaving
							? "Saving…"
							: hasUnsavedFiles
								? "Discard changes and close"
								: isUploading
									? "Cancel upload and close"
									: "Close editor"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
