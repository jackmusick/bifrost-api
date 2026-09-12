import { useEffect, useRef, type RefObject, type ReactNode } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { AlertTitle } from "@/components/ui/alert";
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

type DialogErrorState = string | null;

interface CodeDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	code: string;
	onCodeChange: (value: string) => void;
	onSubmit: () => void;
	isSubmitting: boolean;
	error: DialogErrorState;
	title: string;
	errorTitle: string;
	description: string;
	fieldId: string;
	fieldLabel: string;
	submitLabel: string;
	submitVariant?: "default" | "destructive";
	idleIcon?: ReactNode;
	openerRef?: RefObject<HTMLElement | null>;
	successFocusRef?: RefObject<HTMLElement | null>;
	preferSuccessFocus?: boolean;
	cancelLabel?: string;
}

function CodeDialog({
	open,
	onOpenChange,
	code,
	onCodeChange,
	onSubmit,
	isSubmitting,
	error,
	title,
	errorTitle,
	description,
	fieldId,
	fieldLabel,
	submitLabel,
	submitVariant = "default",
	idleIcon,
	openerRef,
	successFocusRef,
	preferSuccessFocus = false,
	cancelLabel = "Cancel",
}: CodeDialogProps) {
	const errorRef = useRef<HTMLDivElement>(null);
	const opener = useRef<HTMLElement | null>(null);

	useEffect(() => {
		if (!open || !error) return;
		errorRef.current?.focus();
		errorRef.current?.scrollIntoView({ block: "nearest" });
	}, [error, open]);

	return (
		<Dialog
			open={open}
			onOpenChange={(nextOpen) => {
				if (nextOpen) {
					opener.current =
						document.activeElement instanceof HTMLElement
							? document.activeElement
							: (openerRef?.current ?? null);
				}
				if (isSubmitting && !nextOpen) return;
				onOpenChange(nextOpen);
			}}
		>
			<DialogContent
				className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg [&_[data-slot=dialog-header]]:pr-16"
				onOpenAutoFocus={(event) => {
					if (error) {
						event.preventDefault();
						errorRef.current?.focus();
						errorRef.current?.scrollIntoView({ block: "nearest" });
					}
				}}
				onCloseAutoFocus={(event) => {
					event.preventDefault();
					const target = preferSuccessFocus
						? successFocusRef?.current
						: opener.current?.isConnected
							? opener.current
							: openerRef?.current;
					if (target?.isConnected) {
						target.focus({ preventScroll: true });
					}
					opener.current = null;
				}}
				onEscapeKeyDown={(event) => {
					if (isSubmitting) event.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0 pl-6 pr-16 pt-6">
					<DialogTitle>{title}</DialogTitle>
					<DialogDescription>{description}</DialogDescription>
				</DialogHeader>

				<form
					className="flex min-h-0 flex-1 flex-col"
					onSubmit={(event) => {
						event.preventDefault();
						onSubmit();
					}}
				>
					<div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
						<div className="space-y-4">
							<div className="space-y-2">
								<Label htmlFor={fieldId}>{fieldLabel}</Label>
								<Input
									id={fieldId}
									type="text"
									inputMode="numeric"
									pattern="[0-9]*"
									placeholder="Enter 6-digit code"
									value={code}
									onChange={(event) =>
										onCodeChange(
											event.target.value.replace(
												/\D/g,
												"",
											),
										)
									}
									className="text-center text-lg tracking-widest"
									maxLength={6}
									disabled={isSubmitting}
									autoFocus={!error}
								/>
							</div>

							{error && (
								<div
									ref={errorRef}
									role="alert"
									tabIndex={-1}
									className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 outline-none"
								>
									<AlertTitle className="text-sm text-destructive">
										{errorTitle}
									</AlertTitle>
									<p className="mt-1 text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
										{error}
									</p>
								</div>
							)}
						</div>
					</div>

					<DialogFooter className="shrink-0 border-t border-border/70 px-6 py-4">
						<Button
							type="button"
							variant="outline"
							onClick={() => onOpenChange(false)}
							disabled={isSubmitting}
							className="w-full sm:w-auto"
						>
							{cancelLabel}
						</Button>
						<Button
							type="submit"
							variant={submitVariant}
							disabled={isSubmitting || code.length !== 6}
							className="w-full sm:w-auto"
						>
							{isSubmitting ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : idleIcon ? (
								<span className="mr-2 inline-flex">
									{idleIcon}
								</span>
							) : null}
							{isSubmitting ? `${submitLabel}...` : submitLabel}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

export interface SecurityMfaDialogsProps {
	removeOpen: boolean;
	onRemoveOpenChange: (open: boolean) => void;
	removeCode: string;
	onRemoveCodeChange: (value: string) => void;
	onRemove: () => void;
	isRemoving: boolean;
	removeError: DialogErrorState;
	removePreferFallback?: boolean;
	removeReturnFocusRef?: RefObject<HTMLElement | null>;
	removeFallbackRef?: RefObject<HTMLElement | null>;
	regenerateOpen: boolean;
	onRegenerateOpenChange: (open: boolean) => void;
	regenerateCode: string;
	onRegenerateCodeChange: (value: string) => void;
	onRegenerate: () => void;
	isRegenerating: boolean;
	regenerateError: DialogErrorState;
	regeneratePreferFallback?: boolean;
	regenerateReturnFocusRef?: RefObject<HTMLElement | null>;
	regenerateFallbackRef?: RefObject<HTMLElement | null>;
}

export function SecurityMfaDialogs({
	removeOpen,
	onRemoveOpenChange,
	removeCode,
	onRemoveCodeChange,
	onRemove,
	isRemoving,
	removeError,
	removePreferFallback,
	removeReturnFocusRef,
	removeFallbackRef,
	regenerateOpen,
	onRegenerateOpenChange,
	regenerateCode,
	onRegenerateCodeChange,
	onRegenerate,
	isRegenerating,
	regenerateError,
	regeneratePreferFallback,
	regenerateReturnFocusRef,
	regenerateFallbackRef,
}: SecurityMfaDialogsProps) {
	return (
		<>
			<CodeDialog
				open={removeOpen}
				onOpenChange={onRemoveOpenChange}
				code={removeCode}
				onCodeChange={onRemoveCodeChange}
				onSubmit={onRemove}
				isSubmitting={isRemoving}
				error={removeError}
				title="Remove Two-Factor Authentication"
				errorTitle="Unable to remove MFA"
				description="Enter your current authenticator code to remove two-factor authentication from your account."
				fieldId="remove-code"
				fieldLabel="Authenticator Code"
				submitLabel="Remove MFA"
				submitVariant="destructive"
				openerRef={removeReturnFocusRef ?? removeFallbackRef}
				successFocusRef={removeFallbackRef}
				preferSuccessFocus={removePreferFallback}
			/>
			<CodeDialog
				open={regenerateOpen}
				onOpenChange={onRegenerateOpenChange}
				code={regenerateCode}
				onCodeChange={onRegenerateCodeChange}
				onSubmit={onRegenerate}
				isSubmitting={isRegenerating}
				error={regenerateError}
				title="Regenerate Recovery Codes"
				errorTitle="Unable to regenerate recovery codes"
				description="Enter your authenticator code to generate new recovery codes. Your old codes will no longer work."
				fieldId="regenerate-code"
				fieldLabel="Authenticator Code"
				submitLabel="Regenerate"
				idleIcon={<RefreshCw className="h-4 w-4" />}
				openerRef={regenerateReturnFocusRef ?? regenerateFallbackRef}
				successFocusRef={regenerateFallbackRef}
				preferSuccessFocus={regeneratePreferFallback}
			/>
		</>
	);
}

export default SecurityMfaDialogs;
