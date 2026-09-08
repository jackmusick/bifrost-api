import { copyToClipboard } from "@/lib/clipboard";
import { SecurityFeedback } from "./SecurityFeedback";
import { SecurityPasskeyDialogs } from "./SecurityPasskeyDialogs";
import { SecurityMfaDialogs } from "./SecurityMfaDialogs";
/**
 * Security Settings - Passkeys & TOTP Management
 *
 * Allows users to:
 * - Register new passkeys (Face ID, Touch ID, etc.)
 * - View and manage existing passkeys
 * - Set up and manage TOTP (authenticator app)
 * - View and regenerate recovery codes
 */

import { useCallback, useState, useEffect, useRef } from "react";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
	Fingerprint,
	Plus,
	Trash2,
	Loader2,
	Info,
	Smartphone,
	Cloud,
	Clock,
	ShieldCheck,
	AlertTriangle,
	Shield,
	Copy,
	Download,
	CheckCircle,
	Key,
} from "lucide-react";
import {
	useDeletePasskey,
	usePasskeyList,
	usePasskeySupport,
	useRegisterPasskey,
} from "@/hooks/usePasskeys";
import type { PasskeyPublic } from "@/services/passkeys";
import {
	mfaService,
	type MFAStatus,
	type MFASetupResponse,
} from "@/services/mfa";
import { QRCode } from "@/components/ui/QRCode";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

type TOTPSetupStep = "idle" | "setup" | "verify" | "recovery-codes";

export function Security() {
	const support = usePasskeySupport();
	const {
		data: passkeyData,
		isLoading,
		isError,
		isFetching: passkeysFetching,
		refetch: refetchPasskeys,
	} = usePasskeyList();
	const passkeys = passkeyData?.passkeys ?? [];
	const passkeyCount = passkeyData?.count ?? 0;
	const registerPasskeyMutation = useRegisterPasskey({
		showErrorToast: false,
	});
	const deletePasskeyMutation = useDeletePasskey({
		showErrorToast: false,
	});
	const isRegistering = registerPasskeyMutation.isPending;
	const isDeleting = deletePasskeyMutation.isPending;

	// Passkey dialog state
	const [showAddDialog, setShowAddDialog] = useState(false);
	const [deviceName, setDeviceName] = useState("");
	const [passkeyToDelete, setPasskeyToDelete] =
		useState<PasskeyPublic | null>(null);
	const [registerError, setRegisterError] = useState<string | null>(null);
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const [deletePreferFallback, setDeletePreferFallback] = useState(false);
	const registerBusy = useRef(false);
	const deleteBusy = useRef(false);
	const passkeysHeadingRef = useRef<HTMLHeadingElement>(null);

	// MFA state
	const [mfaStatus, setMfaStatus] = useState<MFAStatus | null>(null);
	const [mfaLoading, setMfaLoading] = useState(true);
	const [mfaError, setMfaError] = useState<string | null>(null);
	const mfaHeadingRef = useRef<HTMLHeadingElement>(null);
	const recoveryCodesHeadingRef = useRef<HTMLHeadingElement>(null);

	// TOTP setup state
	const [totpStep, setTotpStep] = useState<TOTPSetupStep>("idle");
	const [totpSetup, setTotpSetup] = useState<MFASetupResponse | null>(null);
	const [totpCode, setTotpCode] = useState("");
	const [totpLoading, setTotpLoading] = useState(false);
	const [totpError, setTotpError] = useState<string | null>(null);
	const [totpCopyError, setTotpCopyError] = useState<string | null>(null);
	const setupBusy = useRef(false);
	const verifyBusy = useRef(false);
	const verifyErrorRef = useRef<HTMLDivElement>(null);
	const [secretCopied, setSecretCopied] = useState(false);

	// Recovery codes state
	const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
	const [recoveryCodesSaved, setRecoveryCodesSaved] = useState(false);
	const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
	const [regenerateCode, setRegenerateCode] = useState("");
	const [regenerateLoading, setRegenerateLoading] = useState(false);
	const [regenerateError, setRegenerateError] = useState<string | null>(null);
	const [regeneratePreferFallback, setRegeneratePreferFallback] =
		useState(false);
	const regenerateBusy = useRef(false);
	const regenerateDialogButtonRef = useRef<HTMLButtonElement>(null);

	// Remove MFA state
	const [showRemoveDialog, setShowRemoveDialog] = useState(false);
	const [removeCode, setRemoveCode] = useState("");
	const [removeLoading, setRemoveLoading] = useState(false);
	const [removeError, setRemoveError] = useState<string | null>(null);
	const [removePreferFallback, setRemovePreferFallback] = useState(false);
	const removeBusy = useRef(false);
	const removeDialogButtonRef = useRef<HTMLButtonElement>(null);

	const loadMFAStatus = useCallback(async () => {
		setMfaLoading(true);
		setMfaError(null);
		try {
			const status = await mfaService.getMFAStatus();
			setMfaStatus(status);
		} catch (err) {
			setMfaError(
				err instanceof Error
					? err.message
					: "Failed to load MFA status",
			);
		} finally {
			setMfaLoading(false);
		}
	}, []);

	// Load MFA status. setState only fires after the awaited fetch resolves
	// — wrapping in a void IIFE keeps the synchronous body free of setState.
	useEffect(() => {
		void (async () => {
			await loadMFAStatus();
		})();
	}, [loadMFAStatus]);

	// Passkey handlers
	const handleRegister = () => {
		if (registerBusy.current) return;
		registerBusy.current = true;
		setRegisterError(null);
		registerPasskeyMutation.mutate(deviceName || undefined, {
			onSuccess: () => {
				registerBusy.current = false;
				setRegisterError(null);
				setShowAddDialog(false);
				setDeviceName("");
			},
			onError: (error) => {
				registerBusy.current = false;
				setRegisterError(error.message);
			},
		});
	};

	const handleDelete = () => {
		if (!passkeyToDelete || deleteBusy.current) return;
		deleteBusy.current = true;
		setDeleteError(null);
		deletePasskeyMutation.mutate(passkeyToDelete.id, {
			onSuccess: () => {
				deleteBusy.current = false;
				setDeleteError(null);
				setDeletePreferFallback(true);
				setPasskeyToDelete(null);
			},
			onError: (error) => {
				deleteBusy.current = false;
				setDeletePreferFallback(false);
				setDeleteError(error.message);
			},
		});
	};

	const getDeviceIcon = (deviceType: string) => {
		if (deviceType === "multiDevice") {
			return <Cloud className="h-5 w-5 text-muted-foreground" />;
		}
		return <Smartphone className="h-5 w-5 text-muted-foreground" />;
	};

	// TOTP handlers
	const handleStartTOTPSetup = async () => {
		if (setupBusy.current || mfaLoading || mfaError) return;
		setupBusy.current = true;
		setTotpLoading(true);
		setTotpError(null);
		try {
			const setup = await mfaService.setupTOTP();
			setTotpSetup(setup);
			setTotpStep("setup");
		} catch (err) {
			setTotpError(
				err instanceof Error
					? err.message
					: "Failed to start TOTP setup",
			);
		} finally {
			setupBusy.current = false;
			setTotpLoading(false);
		}
	};

	const handleVerifyTOTP = async (e: React.FormEvent) => {
		e.preventDefault();
		if (verifyBusy.current || totpCode.length !== 6) return;
		verifyBusy.current = true;
		setTotpLoading(true);
		setTotpError(null);
		setTotpCopyError(null);
		try {
			const result = await mfaService.verifyTOTPSetup(totpCode);
			if (result.success && result.recovery_codes) {
				setRecoveryCodes(result.recovery_codes);
				setRecoveryCodesSaved(false);
				setTotpStep("recovery-codes");
				toast.success("TOTP setup complete!");
				return;
			}
			setTotpError("The code was not accepted. Try again.");
		} catch (err) {
			setTotpError(
				err instanceof Error
					? err.message
					: "Invalid verification code",
			);
		} finally {
			verifyBusy.current = false;
			setTotpLoading(false);
		}
	};

	const handleCompleteTOTPSetup = () => {
		if (!recoveryCodesSaved) return;
		setTotpStep("idle");
		setTotpSetup(null);
		setTotpCode("");
		setRecoveryCodes([]);
		setRecoveryCodesSaved(false);
		loadMFAStatus();
	};

	const handleRemoveMFA = async () => {
		if (
			removeBusy.current ||
			mfaLoading ||
			mfaError ||
			removeCode.length !== 6
		)
			return;
		removeBusy.current = true;
		setRemoveLoading(true);
		setRemoveError(null);
		try {
			await mfaService.removeMFA({ mfa_code: removeCode });
			toast.success("Two-factor authentication removed");
			setRemovePreferFallback(true);
			setShowRemoveDialog(false);
			setRemoveCode("");
			loadMFAStatus();
		} catch (err) {
			setRemoveError(
				err instanceof Error ? err.message : "Failed to remove MFA",
			);
		} finally {
			removeBusy.current = false;
			setRemoveLoading(false);
		}
	};

	const handleRegenerateRecoveryCodes = async () => {
		if (
			regenerateBusy.current ||
			mfaLoading ||
			mfaError ||
			regenerateCode.length !== 6
		)
			return;
		regenerateBusy.current = true;
		setRegenerateLoading(true);
		setRegenerateError(null);
		try {
			const result =
				await mfaService.regenerateRecoveryCodes(regenerateCode);
			setRecoveryCodes(result.recovery_codes);
			setRecoveryCodesSaved(false);
			setRegeneratePreferFallback(true);
			setShowRegenerateDialog(false);
			setRegenerateCode("");
			setTotpStep("recovery-codes");
			toast.success("Recovery codes regenerated");
		} catch (err) {
			setRegenerateError(
				err instanceof Error
					? err.message
					: "Failed to regenerate codes",
			);
		} finally {
			regenerateBusy.current = false;
			setRegenerateLoading(false);
		}
	};

	useEffect(() => {
		if (totpStep !== "verify" || !totpError) return;
		verifyErrorRef.current?.focus();
		verifyErrorRef.current?.scrollIntoView({ block: "nearest" });
	}, [totpError, totpStep]);

	const previousTotpStep = useRef(totpStep);
	useEffect(() => {
		if (previousTotpStep.current === totpStep) return;
		previousTotpStep.current = totpStep;
		const target =
			totpStep === "recovery-codes"
				? recoveryCodesHeadingRef.current
				: totpStep === "idle" || totpStep === "setup"
					? mfaHeadingRef.current
					: null;
		target?.focus();
		target?.scrollIntoView({ block: "nearest" });
	}, [totpStep]);

	const copySecret = async () => {
		if (totpSetup?.secret) {
			if (!(await copyToClipboard(totpSetup.secret))) {
				setTotpCopyError(
					"Could not copy the setup code. Select and copy it manually.",
				);
				return;
			}
			setTotpCopyError(null);
			setSecretCopied(true);
			toast.success("Secret copied to clipboard");
			setTimeout(() => setSecretCopied(false), 2000);
		}
	};

	const copyRecoveryCodes = async () => {
		const text = recoveryCodes.join("\n");
		if (!(await copyToClipboard(text))) {
			setTotpCopyError(
				"Could not copy recovery codes. Download them or copy them manually.",
			);
			return;
		}
		setTotpCopyError(null);
		toast.success("Recovery codes copied to clipboard");
	};

	const downloadRecoveryCodes = () => {
		const text = `Bifrost Recovery Codes
Generated: ${new Date().toISOString()}

These codes can be used to access your account if you lose your authenticator device.
Each code can only be used once.

${recoveryCodes.join("\n")}

Keep these codes in a secure location.
`;
		const blob = new Blob([text], { type: "text/plain" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "bifrost-recovery-codes.txt";
		a.click();
		URL.revokeObjectURL(url);
		toast.success("Recovery codes downloaded");
	};

	// Show loading state for passkeys
	if (support.isLoading) {
		return (
			<Card>
				<CardHeader>
					<Skeleton className="h-6 w-32" />
					<Skeleton className="h-4 w-64 mt-2" />
				</CardHeader>
				<CardContent>
					<Skeleton className="h-20 w-full" />
				</CardContent>
			</Card>
		);
	}

	return (
		<div className="space-y-8">
			{/* Two-Factor Authentication Section */}
			<Card>
				<CardHeader>
					<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
						<div>
							<h2
								ref={mfaHeadingRef}
								tabIndex={-1}
								className="flex items-center gap-2 text-base font-medium outline-none"
							>
								<Shield className="h-5 w-5" />
								Two-Factor Authentication
							</h2>
							<CardDescription className="mt-1">
								Add an extra layer of security with an
								authenticator app
							</CardDescription>
						</div>
						{!mfaLoading &&
							!mfaError &&
							mfaStatus &&
							!mfaStatus.mfa_enabled && (
								<Button
									onClick={handleStartTOTPSetup}
									disabled={totpLoading}
									className="w-full sm:w-auto"
								>
									{totpLoading ? (
										<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
									) : (
										<Plus className="mr-2 h-4 w-4" />
									)}
									Set Up
								</Button>
							)}
					</div>
				</CardHeader>
				<CardContent>
					{/* Loading state */}
					{mfaLoading && (
						<div className="space-y-3">
							<Skeleton className="h-16 w-full" />
						</div>
					)}

					{/* Error state */}
					{mfaError && (
						<SecurityFeedback
							message="Couldn't load two-factor authentication status."
							retryLabel="Retry authentication status"
							pending={mfaLoading}
							onRetry={() => void loadMFAStatus()}
						/>
					)}
					{totpStep === "idle" && totpError && (
						<SecurityFeedback
							message={totpError}
							retryLabel="Retry authenticator setup"
							pending={totpLoading}
							onRetry={() => void handleStartTOTPSetup()}
							focus
						/>
					)}

					{/* MFA not enabled */}
					{!mfaLoading &&
						!mfaError &&
						mfaStatus &&
						!mfaStatus.mfa_enabled &&
						totpStep === "idle" && (
							<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 py-8 text-center text-muted-foreground">
								<Shield className="mx-auto mb-4 h-12 w-12 opacity-50" />
								<p className="font-medium">
									Two-factor authentication not enabled
								</p>
								<p className="text-sm mt-1">
									Protect your account with an authenticator
									app
								</p>
							</div>
						)}

					{/* MFA enabled */}
					{!mfaLoading &&
						!mfaError &&
						mfaStatus &&
						mfaStatus.mfa_enabled &&
						totpStep === "idle" && (
							<div className="space-y-4">
								<div className="flex flex-col gap-4 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
									<div className="flex items-start gap-4">
										<div className="rounded-full bg-[var(--bf-success-soft)] p-2 text-[var(--bf-success)] dark:bg-[var(--bf-success-soft)] dark:text-[var(--bf-success)]">
											<ShieldCheck className="h-5 w-5 text-[var(--bf-success)]" />
										</div>
										<div>
											<div className="flex items-center gap-2">
												<span className="font-medium">
													Authenticator App
												</span>
												<Badge
													variant="secondary"
													className="border-[var(--bf-success)]/20 bg-[var(--bf-success)]/10 text-[var(--bf-success)] text-xs"
												>
													Enabled
												</Badge>
											</div>
											<p className="text-sm text-muted-foreground mt-1">
												{
													mfaStatus.recovery_codes_remaining
												}{" "}
												recovery codes remaining
											</p>
										</div>
									</div>
									<div className="flex flex-col gap-2 sm:flex-row">
										<Button
											ref={regenerateDialogButtonRef}
											variant="outline"
											size="sm"
											onClick={() => {
												setRegenerateError(null);
												setRegeneratePreferFallback(
													false,
												);
												setShowRegenerateDialog(true);
											}}
											className="w-full sm:w-auto"
										>
											<Key className="mr-2 h-4 w-4" />
											Recovery Codes
										</Button>
										<Button
											ref={removeDialogButtonRef}
											variant="outline"
											size="sm"
											onClick={() => {
												setRemoveError(null);
												setRemovePreferFallback(false);
												setShowRemoveDialog(true);
											}}
											className="w-full border-destructive/20 text-destructive hover:bg-destructive/5 hover:text-destructive sm:w-auto"
										>
											<Trash2 className="mr-2 h-4 w-4" />
											Remove
										</Button>
									</div>
								</div>
							</div>
						)}

					{/* TOTP Setup Flow */}
					{totpStep === "setup" && totpSetup && (
						<div className="space-y-4">
							<Alert>
								<Info className="h-4 w-4" />
								<AlertDescription>
									Scan this QR code with your authenticator
									app (Google Authenticator, Authy, 1Password,
									etc.)
								</AlertDescription>
							</Alert>

							<div className="flex items-center justify-center rounded-[var(--bf-radius-surface)] border border-border/70 bg-white p-4 dark:bg-card">
								<QRCode
									data={totpSetup.qr_code_uri}
									size={200}
									alt="TOTP QR Code"
								/>
							</div>

							<div className="space-y-2 text-center">
								<p className="text-xs text-muted-foreground">
									Or enter this code manually:
								</p>
								<div className="flex items-center justify-center gap-2">
									<code className="min-w-0 break-all rounded-[var(--bf-radius-control)] bg-muted px-2 py-1 font-mono text-sm">
										{totpSetup.secret}
									</code>
									<Button
										variant="ghost"
										size="sm"
										onClick={copySecret}
										aria-label={
											secretCopied
												? "Setup code copied"
												: "Copy setup code"
										}
										className="h-11 min-w-11 shrink-0 px-2 sm:h-7 sm:min-w-0"
									>
										{secretCopied ? (
											<CheckCircle className="h-3 w-3 text-[var(--bf-success)]" />
										) : (
											<Copy className="h-3 w-3" />
										)}
									</Button>
								</div>
							</div>
							{totpCopyError && (
								<Alert variant="destructive">
									<AlertTriangle className="h-4 w-4" />
									<AlertDescription>
										{totpCopyError}
									</AlertDescription>
								</Alert>
							)}

							<div className="flex flex-col gap-2 sm:flex-row">
								<Button
									variant="outline"
									className="w-full sm:flex-1"
									onClick={() => {
										setTotpStep("idle");
										setTotpSetup(null);
										setTotpCopyError(null);
									}}
								>
									Cancel
								</Button>
								<Button
									className="w-full sm:flex-1"
									onClick={() => setTotpStep("verify")}
								>
									Continue
								</Button>
							</div>
						</div>
					)}

					{/* TOTP Verify Step */}
					{totpStep === "verify" && (
						<form onSubmit={handleVerifyTOTP} className="space-y-4">
							{totpError && (
								<div
									ref={verifyErrorRef}
									role="alert"
									tabIndex={-1}
									className="rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 outline-none"
								>
									<AlertTitle className="text-sm text-destructive">
										Verification failed
									</AlertTitle>
									<p className="mt-1 text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
										{totpError}
									</p>
								</div>
							)}

							<div className="space-y-2">
								<Label htmlFor="totp-code">
									Verification Code
								</Label>
								<Input
									id="totp-code"
									type="text"
									inputMode="numeric"
									pattern="[0-9]*"
									placeholder="Enter 6-digit code"
									value={totpCode}
									onChange={(e) =>
										setTotpCode(
											e.target.value.replace(/\D/g, ""),
										)
									}
									className="text-center text-lg tracking-widest"
									maxLength={6}
									autoFocus
									disabled={totpLoading}
								/>
								<p className="text-xs text-muted-foreground text-center">
									Enter the code from your authenticator app
								</p>
							</div>

							<div className="flex gap-2">
								<Button
									type="button"
									variant="outline"
									className="flex-1"
									onClick={() => setTotpStep("setup")}
									disabled={totpLoading}
								>
									Back
								</Button>
								<Button
									type="submit"
									className="flex-1"
									disabled={
										totpLoading || totpCode.length !== 6
									}
								>
									{totpLoading ? (
										<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
									) : null}
									Verify
								</Button>
							</div>
						</form>
					)}

					{/* Recovery Codes Step */}
					{totpStep === "recovery-codes" && (
						<div className="space-y-4">
							<h3
								ref={recoveryCodesHeadingRef}
								tabIndex={-1}
								className="text-base font-medium outline-none"
							>
								Recovery codes
							</h3>
							<Alert>
								<AlertTriangle className="h-4 w-4" />
								<AlertTitle>
									Save your recovery codes
								</AlertTitle>
								<AlertDescription>
									These codes can be used to access your
									account if you lose your authenticator. Each
									code can only be used once. Store them
									securely.
								</AlertDescription>
							</Alert>

							<div className="grid grid-cols-1 gap-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/50 p-4 font-mono text-sm sm:grid-cols-2">
								{recoveryCodes.map((code, i) => (
									<div
										key={i}
										className="break-all py-1 text-center"
									>
										{code}
									</div>
								))}
							</div>

							<div className="flex flex-col gap-2 sm:flex-row">
								<Button
									variant="outline"
									className="w-full sm:flex-1"
									onClick={() => {
										setTotpCopyError(null);
										void copyRecoveryCodes();
									}}
								>
									<Copy className="mr-2 h-4 w-4" />
									Copy
								</Button>
								<Button
									variant="outline"
									className="w-full sm:flex-1"
									onClick={downloadRecoveryCodes}
								>
									<Download className="mr-2 h-4 w-4" />
									Download
								</Button>
							</div>
							{totpCopyError && (
								<Alert variant="destructive">
									<AlertTriangle className="h-4 w-4" />
									<AlertDescription>
										{totpCopyError}
									</AlertDescription>
								</Alert>
							)}

							<div className="flex items-start gap-2">
								<Checkbox
									id="savedCodes"
									checked={recoveryCodesSaved}
									onCheckedChange={(checked) =>
										setRecoveryCodesSaved(checked === true)
									}
								/>
								<Label
									htmlFor="savedCodes"
									className="text-sm font-normal leading-6"
								>
									I have saved my recovery codes
								</Label>
							</div>

							<Button
								onClick={handleCompleteTOTPSetup}
								className="w-full"
								disabled={!recoveryCodesSaved}
							>
								<CheckCircle className="mr-2 h-4 w-4" />
								Done
							</Button>
						</div>
					)}
				</CardContent>
			</Card>

			{/* Passkeys Section */}
			<Card>
				<CardHeader>
					<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
						<div>
							<h2
								ref={passkeysHeadingRef}
								tabIndex={-1}
								className="flex items-center gap-2 outline-none"
							>
								<Fingerprint className="h-5 w-5" />
								Passkeys
							</h2>
							<CardDescription className="mt-1">
								Sign in faster with Face ID, Touch ID, or
								security keys
							</CardDescription>
						</div>
						{support.supported && (
							<Button
								onClick={() => {
									setRegisterError(null);
									setShowAddDialog(true);
								}}
								className="w-full sm:w-auto"
							>
								<Plus className="mr-2 h-4 w-4" />
								Add Passkey
							</Button>
						)}
					</div>
				</CardHeader>
				<CardContent>
					{/* Unsupported browser */}
					{!support.supported && (
						<Alert variant="default">
							<AlertTriangle className="h-4 w-4" />
							<AlertTitle>Passkeys not supported</AlertTitle>
							<AlertDescription>
								Your browser doesn't support passkeys. Try using
								a modern browser like Chrome, Safari, or Edge on
								a device with biometric authentication.
							</AlertDescription>
						</Alert>
					)}

					{support.supported && (
						<>
							{/* Info banner */}
							<Alert className="mb-6 border-border/70 bg-muted/40">
								<ShieldCheck className="h-4 w-4" />
								<AlertTitle>Passwordless login</AlertTitle>
								<AlertDescription>
									Passkeys let you sign in without a password
									using biometrics or your device PIN. They're
									phishing resistant and more secure than
									passwords.
								</AlertDescription>
							</Alert>

							{/* Loading state */}
							{isLoading && (
								<div className="space-y-3">
									<Skeleton className="h-16 w-full" />
									<Skeleton className="h-16 w-full" />
								</div>
							)}

							{/* Error state */}
							{isError && (
								<SecurityFeedback
									message={
										passkeyCount > 0
											? "Couldn't refresh passkeys. Previously loaded devices are shown below."
											: "Couldn't load your passkeys."
									}
									retryLabel="Retry passkeys"
									pending={passkeysFetching}
									onRetry={() => void refetchPasskeys()}
								/>
							)}

							{/* Empty state */}
							{!isLoading && !isError && passkeyCount === 0 && (
								<div className="text-center py-8 text-muted-foreground">
									<Fingerprint className="h-12 w-12 mx-auto mb-4 opacity-50" />
									<p className="font-medium">
										No passkeys yet
									</p>
									<p className="text-sm mt-1">
										Add a passkey to enable passwordless
										sign-in
									</p>
								</div>
							)}

							{/* Passkey list */}
							{!isLoading && passkeyCount > 0 && (
								<div className="space-y-3">
									{passkeys.map((passkey) => (
										<div
											key={passkey.id}
											className="flex flex-col gap-4 rounded-[var(--bf-radius-surface)] border border-border/70 p-4 transition-colors hover:bg-muted/50 sm:flex-row sm:items-center sm:justify-between"
										>
											<div className="flex min-w-0 items-start gap-4">
												{getDeviceIcon(
													passkey.device_type,
												)}
												<div className="min-w-0">
													<div className="flex flex-wrap items-center gap-2">
														<span className="min-w-0 font-medium">
															{passkey.name}
														</span>
														{passkey.backed_up && (
															<Badge
																variant="secondary"
																className="border-[var(--bf-success)]/20 bg-[var(--bf-success)]/10 text-[var(--bf-success)] text-xs"
															>
																<Cloud className="h-3 w-3 mr-1" />
																Synced
															</Badge>
														)}
													</div>
													<div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
														<span className="flex items-center gap-1">
															<Clock className="h-3 w-3" />
															Created{" "}
															{formatDistanceToNow(
																new Date(
																	passkey.created_at,
																),
																{
																	addSuffix: true,
																},
															)}
														</span>
														{passkey.last_used_at && (
															<span>
																Last used{" "}
																{formatDistanceToNow(
																	new Date(
																		passkey.last_used_at,
																	),
																	{
																		addSuffix: true,
																	},
																)}
															</span>
														)}
													</div>
												</div>
											</div>
											<Button
												variant="ghost"
												size="icon"
												className="h-11 w-11 text-destructive hover:bg-destructive/10 hover:text-destructive sm:h-9 sm:w-9"
												aria-label={`Remove passkey ${passkey.name}`}
												onClick={() => {
													setDeleteError(null);
													setDeletePreferFallback(
														false,
													);
													setPasskeyToDelete(passkey);
												}}
											>
												<Trash2 className="h-4 w-4" />
											</Button>
										</div>
									))}
								</div>
							)}
						</>
					)}
				</CardContent>
			</Card>

			<SecurityPasskeyDialogs
				addOpen={showAddDialog}
				onAddOpenChange={(open) => {
					setRegisterError(null);
					if (open) {
						setDeviceName("");
					}
					setShowAddDialog(open);
				}}
				deviceName={deviceName}
				onDeviceNameChange={setDeviceName}
				onRegister={handleRegister}
				isRegistering={isRegistering}
				registerError={registerError}
				passkeyToDelete={passkeyToDelete}
				onDeleteOpenChange={(open) => {
					if (open) {
						setDeleteError(null);
						setDeletePreferFallback(false);
						return;
					}
					if (deleteBusy.current) return;
					setDeletePreferFallback(false);
					setDeleteError(null);
					setPasskeyToDelete(null);
				}}
				onDelete={handleDelete}
				isDeleting={isDeleting}
				deleteError={deleteError}
				deletePreferFallback={deletePreferFallback}
				returnFocusRef={passkeysHeadingRef}
			/>

			<SecurityMfaDialogs
				removeOpen={showRemoveDialog}
				onRemoveOpenChange={(open) => {
					if (open) {
						setRemoveError(null);
						setRemovePreferFallback(false);
						return;
					}
					if (removeBusy.current) return;
					setRemoveError(null);
					setRemoveCode("");
					setShowRemoveDialog(false);
				}}
				removeCode={removeCode}
				onRemoveCodeChange={setRemoveCode}
				onRemove={handleRemoveMFA}
				isRemoving={removeLoading}
				removeError={removeError}
				removePreferFallback={removePreferFallback}
				removeReturnFocusRef={removeDialogButtonRef}
				removeFallbackRef={mfaHeadingRef}
				regenerateOpen={showRegenerateDialog}
				onRegenerateOpenChange={(open) => {
					if (open) {
						setRegenerateError(null);
						setRegeneratePreferFallback(false);
						return;
					}
					if (regenerateBusy.current) return;
					setRegenerateError(null);
					setRegenerateCode("");
					setShowRegenerateDialog(false);
				}}
				regenerateCode={regenerateCode}
				onRegenerateCodeChange={setRegenerateCode}
				onRegenerate={handleRegenerateRecoveryCodes}
				isRegenerating={regenerateLoading}
				regenerateError={regenerateError}
				regeneratePreferFallback={regeneratePreferFallback}
				regenerateReturnFocusRef={regenerateDialogButtonRef}
				regenerateFallbackRef={recoveryCodesHeadingRef}
			/>
		</div>
	);
}
