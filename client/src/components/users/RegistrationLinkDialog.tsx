import { useEffect, useRef, useState } from "react";
import { Check, Copy, Info, Loader2, Mail, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { getErrorMessage } from "@/lib/api-error";
import { copyToClipboard } from "@/lib/clipboard";

interface RegistrationLinkDialogProps {
	open: boolean;
	title?: string;
	email?: string;
	url?: string;
	canSendEmail: boolean;
	isSendingEmail?: boolean;
	onOpenChange: (open: boolean) => void;
	onSendEmail?: () => void | Promise<void>;
}

function absoluteRegistrationUrl(url: string): string {
	try {
		return new URL(url, window.location.origin).toString();
	} catch {
		return url;
	}
}

export function RegistrationLinkDialog({
	open,
	title = "User Created",
	email,
	url,
	canSendEmail,
	isSendingEmail = false,
	onOpenChange,
	onSendEmail,
}: RegistrationLinkDialogProps) {
	const normalizedUrl = url ? absoluteRegistrationUrl(url) : "";
	const [sending, setSending] = useState(false);
	const sendBusy = useRef(false);
	const [sendError, setSendError] = useState<string | null>(null);
	const errorRef = useRef<HTMLDivElement>(null);
	const busy = sending || isSendingEmail;
	const sendDisabled =
		!canSendEmail || !normalizedUrl || busy || !onSendEmail;
	useEffect(() => {
		if (sendError) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [sendError]);
	const [copied, setCopied] = useState(false);

	useEffect(() => {
		if (!copied) return;
		const timer = window.setTimeout(() => setCopied(false), 1600);
		return () => window.clearTimeout(timer);
	}, [copied]);

	const handleCopy = async () => {
		if (!normalizedUrl) return;
		if (await copyToClipboard(normalizedUrl)) {
			setCopied(true);
			toast.success("Registration link copied");
		} else {
			setCopied(false);
			toast.error("Failed to copy registration link");
		}
	};

	const handleSendEmail = async () => {
		if (sendDisabled || sendBusy.current || !onSendEmail) return;
		sendBusy.current = true;
		setSending(true);
		setSendError(null);
		try {
			await onSendEmail();
		} catch (error) {
			setSendError(
				getErrorMessage(error, "The email service is unavailable."),
			);
		} finally {
			sendBusy.current = false;
			setSending(false);
		}
	};

	const sendButton = (
		<Button
			type="button"
			className="h-11 w-full"
			onClick={handleSendEmail}
			disabled={sendDisabled}
		>
			{busy ? (
				<Loader2 className="mr-2 h-4 w-4 motion-safe:animate-spin" />
			) : (
				<Mail className="mr-2 h-4 w-4" />
			)}
			{busy ? "Sending registration email…" : "Send Registration Email"}
			{!canSendEmail && <Info className="ml-2 h-4 w-4 opacity-80" />}
		</Button>
	);

	return (
		<Dialog
			open={open}
			onOpenChange={(nextOpen) => {
				if (!busy) onOpenChange(nextOpen);
			}}
		>
			<DialogContent
				showCloseButton={false}
				onEscapeKeyDown={(event) => {
					if (busy) event.preventDefault();
				}}
				onInteractOutside={(event) => {
					if (busy) event.preventDefault();
				}}
				className="flex max-h-[90dvh] max-w-md flex-col gap-0 overflow-y-auto border-border/70 p-0 shadow-xl motion-reduce:transition-none motion-reduce:animate-none"
			>
				<DialogHeader className="relative items-center border-b border-border/70 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] text-center sm:px-6">
					<Button
						type="button"
						variant="ghost"
						size="icon-lg"
						onClick={() => onOpenChange(false)}
						aria-label="Close dialog"
						disabled={busy}
						className="absolute right-4 top-[max(1rem,env(safe-area-inset-top))] h-11 w-11 rounded-[var(--bf-radius-control)] border border-border/70 bg-background/90 text-foreground hover:bg-muted motion-reduce:transition-none"
					>
						<X className="h-5 w-5" />
					</Button>
					<div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]">
						<Check className="h-6 w-6" />
					</div>
					<DialogTitle>{title}</DialogTitle>
					<DialogDescription className="max-w-sm [overflow-wrap:anywhere]">
						{email
							? `Send this to ${email} so they can finish logging in. They can also log in with SSO and register themselves automatically.`
							: "Send this to the user so they can finish logging in. They can also log in with SSO and register themselves automatically."}
					</DialogDescription>
				</DialogHeader>

				<div
					className="min-h-0 space-y-2 px-4 py-4 sm:px-6"
					aria-busy={busy}
				>
					{sendError && (
						<div
							ref={errorRef}
							tabIndex={-1}
							role="alert"
							className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 text-sm outline-none [overflow-wrap:anywhere]"
						>
							<p className="font-medium text-destructive">
								Registration email was not sent
							</p>
							<p className="mt-1 text-muted-foreground">
								{sendError}
							</p>
							<p className="mt-1 text-muted-foreground">
								Try sending again, or copy the link below.
							</p>
						</div>
					)}
					{canSendEmail ? (
						sendButton
					) : (
						<Tooltip>
							<TooltipTrigger asChild>
								<span
									tabIndex={0}
									aria-label="Registration email automation setup"
									className="inline-flex w-full cursor-help"
								>
									{sendButton}
								</span>
							</TooltipTrigger>
							<TooltipContent className="max-w-xs">
								Create an active{" "}
								<span className="font-mono">user.invited</span>{" "}
								event source with at least one subscription to
								enable registration emails.
							</TooltipContent>
						</Tooltip>
					)}

					<Button
						type="button"
						variant="outline"
						className="h-11 w-full"
						onClick={handleCopy}
						disabled={!normalizedUrl}
					>
						{copied ? (
							<Check className="mr-2 h-4 w-4 text-[var(--bf-success)]" />
						) : (
							<Copy className="mr-2 h-4 w-4" />
						)}
						{copied ? "Copied" : "Copy Registration Link"}
					</Button>
				</div>
			</DialogContent>
		</Dialog>
	);
}
