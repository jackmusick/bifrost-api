import { useEffect, useRef, type RefObject } from "react";

import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
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
import type { ChatArtifactPublic } from "@/services/chatAttachments";

export function ArtifactRenameDialog({
	open,
	filename,
	pending,
	error,
	onOpenChange,
	onFilenameChange,
	onSubmit,
	returnFocusRef,
}: {
	open: boolean;
	filename: string;
	pending: boolean;
	error: string | null;
	onOpenChange: (open: boolean) => void;
	onFilenameChange: (filename: string) => void;
	onSubmit: () => void;
	returnFocusRef?: RefObject<HTMLElement | null>;
}) {
	const inputRef = useRef<HTMLInputElement>(null);
	const errorRef = useRef<HTMLParagraphElement>(null);
	const focus = useDialogReturnFocus(returnFocusRef);

	useEffect(() => {
		if (!open || !error) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [error, open]);

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!pending) onOpenChange(next);
			}}
		>
			<DialogContent
				{...focus}
				className="flex max-h-[90dvh] flex-col overflow-hidden"
				onOpenAutoFocus={(event) => {
					focus.onOpenAutoFocus();
					if (error) {
						event.preventDefault();
						errorRef.current?.focus();
						return;
					}
					event.preventDefault();
					inputRef.current?.focus();
				}}
				onEscapeKeyDown={(event) => {
					if (pending) event.preventDefault();
				}}
				onPointerDownOutside={(event) => {
					if (pending) event.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0">
					<DialogTitle>Rename artifact</DialogTitle>
					<DialogDescription>
						Choose the filename shown in Chat and your artifact
						library.
					</DialogDescription>
				</DialogHeader>

				<form
					className="flex min-h-0 flex-1 flex-col"
					onSubmit={(event) => {
						event.preventDefault();
						if (pending || !filename.trim()) return;
						onSubmit();
					}}
				>
					<div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-4">
						<fieldset
							disabled={pending}
							className="min-w-0 space-y-4"
						>
							<div className="space-y-2">
								<Label htmlFor="artifact-filename">
									Filename
								</Label>
								<Input
									ref={inputRef}
									id="artifact-filename"
									className="min-h-11"
									value={filename}
									onChange={(event) =>
										onFilenameChange(event.target.value)
									}
								/>
							</div>
						</fieldset>

						{error && (
							<p
								ref={errorRef}
								role="alert"
								tabIndex={-1}
								className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive outline-none [overflow-wrap:anywhere]"
							>
								Could not rename this artifact. Your filename is
								preserved. Try again.
							</p>
						)}
					</div>

					<DialogFooter className="shrink-0 border-t pt-4 [&>button]:min-h-11">
						<Button
							type="button"
							variant="outline"
							disabled={pending}
							onClick={() => onOpenChange(false)}
						>
							Cancel
						</Button>
						<Button
							type="submit"
							disabled={!filename.trim() || pending}
						>
							{pending ? "Renaming…" : "Rename"}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

export function ArtifactDeleteDialog({
	open,
	target,
	pending,
	error,
	preferFallback,
	fallbackRef,
	onOpenChange,
	onConfirm,
	returnFocusRef,
}: {
	open: boolean;
	target: ChatArtifactPublic | null;
	pending: boolean;
	error: string | null;
	preferFallback: boolean;
	fallbackRef?: RefObject<HTMLElement | null>;
	onOpenChange: (open: boolean) => void;
	onConfirm: () => void;
	returnFocusRef?: RefObject<HTMLElement | null>;
}) {
	const errorRef = useRef<HTMLParagraphElement>(null);
	const focus = useDialogReturnFocus(
		preferFallback ? fallbackRef : returnFocusRef,
		preferFallback,
	);

	useEffect(() => {
		if (!open || !error) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [error, open]);

	return (
		<AlertDialog
			open={open}
			onOpenChange={(next) => {
				if (!pending) onOpenChange(next);
			}}
		>
			<AlertDialogContent
				{...focus}
				className="flex max-h-[90dvh] flex-col overflow-hidden"
				onOpenAutoFocus={(event) => {
					focus.onOpenAutoFocus();
					if (error) {
						event.preventDefault();
						errorRef.current?.focus();
					}
				}}
				onEscapeKeyDown={(event) => {
					if (pending) event.preventDefault();
				}}
			>
				<AlertDialogHeader className="shrink-0">
					<AlertDialogTitle>Delete artifact?</AlertDialogTitle>
				</AlertDialogHeader>

				<div className="min-h-0 flex-1 space-y-4 overflow-y-auto text-center sm:text-left">
					<AlertDialogDescription className="[overflow-wrap:anywhere]">
						{target?.filename} will be removed from its conversation
						and cannot be recovered.
					</AlertDialogDescription>
					{error && (
						<p
							ref={errorRef}
							role="alert"
							tabIndex={-1}
							className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive outline-none [overflow-wrap:anywhere]"
						>
							Could not delete this artifact. Try again.
						</p>
					)}
				</div>

				<AlertDialogFooter className="shrink-0 border-t pt-4">
					<AlertDialogCancel disabled={pending}>
						Cancel
					</AlertDialogCancel>
					<AlertDialogAction
						variant="destructive"
						disabled={pending}
						onClick={(event) => {
							event.preventDefault();
							onConfirm();
						}}
					>
						{pending ? "Deleting…" : "Delete"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
