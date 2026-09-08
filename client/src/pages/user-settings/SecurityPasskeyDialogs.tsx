import { useEffect, useRef, type RefObject } from "react";
import { Fingerprint, Loader2 } from "lucide-react";

import { AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	AlertDialog,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import type { PasskeyPublic } from "@/services/passkeys";

type DialogErrorState = string | null;

export interface SecurityPasskeyDialogsProps {
	addOpen: boolean;
	onAddOpenChange: (open: boolean) => void;
	deviceName: string;
	onDeviceNameChange: (value: string) => void;
	onRegister: () => void;
	isRegistering: boolean;
	registerError: DialogErrorState;
	passkeyToDelete: PasskeyPublic | null;
	onDeleteOpenChange: (open: boolean) => void;
	onDelete: () => void;
	isDeleting: boolean;
	deleteError: DialogErrorState;
	deletePreferFallback?: boolean;
	returnFocusRef?: RefObject<HTMLElement | null>;
}

function PasskeyAddDialog({
	addOpen,
	onAddOpenChange,
	deviceName,
	onDeviceNameChange,
	onRegister,
	isRegistering,
	registerError,
	returnFocusRef,
}: Pick<
	SecurityPasskeyDialogsProps,
	| "addOpen"
	| "onAddOpenChange"
	| "deviceName"
	| "onDeviceNameChange"
	| "onRegister"
	| "isRegistering"
	| "registerError"
	| "returnFocusRef"
>) {
	const errorRef = useRef<HTMLDivElement>(null);
	const returnFocus = useDialogReturnFocus(returnFocusRef);

	useEffect(() => {
		if (!addOpen || !registerError) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [addOpen, registerError]);

	return (
		<Dialog
			open={addOpen}
			onOpenChange={(open) => {
				if (isRegistering && !open) return;
				onAddOpenChange(open);
			}}
		>
			<DialogContent
				className="flex max-h-[90dvh] flex-col overflow-hidden"
				{...returnFocus}
				onOpenAutoFocus={(event) => {
					returnFocus.onOpenAutoFocus();
					if (registerError) {
						event.preventDefault();
						errorRef.current?.focus();
						errorRef.current?.scrollIntoView({ block: "nearest" });
					}
				}}
				onEscapeKeyDown={(event) => {
					if (isRegistering) event.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0">
					<DialogTitle className="flex items-center gap-2">
						<Fingerprint className="h-5 w-5" />
						Add Passkey
					</DialogTitle>
					<DialogDescription>
						Register a new passkey for passwordless sign-in. You'll
						be prompted to use Face ID, Touch ID, or your device
						PIN.
					</DialogDescription>
				</DialogHeader>

				<form
					className="flex min-h-0 flex-1 flex-col"
					onSubmit={(event) => {
						event.preventDefault();
						onRegister();
					}}
				>
					<div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-4">
						<div className="space-y-2">
							<Label htmlFor="device-name">
								Device Name (optional)
							</Label>
							<Input
								id="device-name"
								placeholder='e.g., "MacBook Pro" or "iPhone"'
								value={deviceName}
								onChange={(event) =>
									onDeviceNameChange(event.target.value)
								}
								disabled={isRegistering}
							/>
							<p className="text-xs text-muted-foreground">
								A friendly name to help you identify this
								passkey later
							</p>
						</div>

						{registerError && (
							<div
								ref={errorRef}
								role="alert"
								tabIndex={-1}
								className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 outline-none"
							>
								<AlertTitle className="text-sm text-destructive">
									Passkey could not be registered
								</AlertTitle>
								<p className="mt-1 text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
									{registerError}
								</p>
							</div>
						)}
					</div>

					<DialogFooter className="shrink-0 pt-4">
						<Button
							type="button"
							variant="outline"
							onClick={() => onAddOpenChange(false)}
							disabled={isRegistering}
							className="w-full sm:w-auto"
						>
							Cancel
						</Button>
						<Button
							type="submit"
							disabled={isRegistering}
							className="w-full sm:w-auto"
						>
							{isRegistering ? (
								<>
									<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
									Registering...
								</>
							) : (
								<>
									<Fingerprint className="mr-2 h-4 w-4" />
									Register Passkey
								</>
							)}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

function PasskeyDeleteDialog({
	passkeyToDelete,
	onDeleteOpenChange,
	onDelete,
	isDeleting,
	deleteError,
	deletePreferFallback,
	returnFocusRef,
}: Pick<
	SecurityPasskeyDialogsProps,
	| "passkeyToDelete"
	| "onDeleteOpenChange"
	| "onDelete"
	| "isDeleting"
	| "deleteError"
	| "deletePreferFallback"
	| "returnFocusRef"
>) {
	const errorRef = useRef<HTMLDivElement>(null);
	const returnFocus = useDialogReturnFocus(
		returnFocusRef,
		deletePreferFallback === true,
	);
	const open = !!passkeyToDelete;

	useEffect(() => {
		if (!open || !deleteError) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [deleteError, open]);

	return (
		<AlertDialog
			open={open}
			onOpenChange={(nextOpen) => {
				if (isDeleting && !nextOpen) return;
				onDeleteOpenChange(nextOpen);
			}}
		>
			<AlertDialogContent
				{...returnFocus}
				onOpenAutoFocus={(event) => {
					returnFocus.onOpenAutoFocus();
					if (deleteError) {
						event.preventDefault();
						errorRef.current?.focus();
						errorRef.current?.scrollIntoView({ block: "nearest" });
					}
				}}
				onEscapeKeyDown={(event) => {
					if (isDeleting) event.preventDefault();
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle>Remove Passkey?</AlertDialogTitle>
					<AlertDialogDescription className="[overflow-wrap:anywhere]">
						Are you sure you want to remove "{passkeyToDelete?.name}
						"? You won't be able to use this passkey to sign in
						anymore.
					</AlertDialogDescription>
				</AlertDialogHeader>

				{deleteError && (
					<div
						ref={errorRef}
						role="alert"
						tabIndex={-1}
						className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 outline-none"
					>
						<AlertTitle className="text-sm text-destructive">
							Passkey could not be removed
						</AlertTitle>
						<p className="mt-1 text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
							{deleteError}
						</p>
					</div>
				)}

				<AlertDialogFooter>
					<Button
						type="button"
						variant="outline"
						onClick={() => onDeleteOpenChange(false)}
						disabled={isDeleting}
						className="min-h-11"
					>
						Cancel
					</Button>
					<Button
						type="button"
						variant="destructive"
						disabled={isDeleting}
						className="min-h-11"
						onClick={() => onDelete()}
					>
						{isDeleting ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
								Removing...
							</>
						) : (
							"Remove Passkey"
						)}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}

export function SecurityPasskeyDialogs(props: SecurityPasskeyDialogsProps) {
	return (
		<>
			<PasskeyAddDialog {...props} />
			<PasskeyDeleteDialog {...props} />
		</>
	);
}

export default SecurityPasskeyDialogs;
