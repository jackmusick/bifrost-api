import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { useRef, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Loader2, Shield, CheckCircle2, AlertCircle, Trash2, Copy, Key } from "lucide-react";
import { toast } from "sonner";
import type { OAuthProvider } from "@/services/oauth-config";

interface ProviderCardProps {
	provider: OAuthProvider;
	title: string;
	description: string;
	configured: boolean;
	clientId?: string | null;
	clientSecretSet: boolean;
	extraFields?: { label: string; value?: string | null }[];
	callbackUrl: string;
	onSave: () => Promise<void>;
	onEdit: () => void;
	onCancel: () => void;
	onDelete: () => Promise<void>;
	onTest: () => Promise<{ success: boolean; message: string }>;
	children: React.ReactNode;
}

export function OAuthProviderCard({
	provider,
	title,
	description,
	configured,
	clientId,
	clientSecretSet,
	extraFields,
	callbackUrl,
	onSave,
	onEdit,
	onCancel,
	onDelete,
	onTest,
	children,
}: ProviderCardProps) {
	const [isEditing, setIsEditing] = useState(!configured);
	const [saving, setSaving] = useState(false);
	const [testing, setTesting] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [testResult, setTestResult] = useState<{
		success: boolean;
		message: string;
	} | null>(null);
	const [saveFailed, setSaveFailed] = useState(false);
	const [deleteFailed, setDeleteFailed] = useState(false);
	const busy = saving || testing;
	const headingRef = useRef<HTMLDivElement>(null);
	const [removed, setRemoved] = useState(false);
	const dialogFocus = useDialogReturnFocus(headingRef, removed);

	const handleCopyCallback = async () => {
		try {
			await navigator.clipboard.writeText(callbackUrl);
			toast.success("Callback URL copied to clipboard");
		} catch {
			toast.error("Could not copy callback URL", { description: "Select and copy the URL above." });
		}
	};

	const handleTest = async () => {
		if (busy) return;
		setTesting(true);
		setTestResult(null);
		try {
			const result = await onTest();
			setTestResult(result);
			if (result.success) {
				toast.success("Connection test passed", {
					description: result.message,
				});
			} else {
				toast.error("Connection test failed", {
					description: result.message,
				});
			}
		} catch (error) {
			const message =
				error instanceof Error ? error.message : "Unknown error";
			setTestResult({ success: false, message });
			toast.error("Test failed", { description: message });
		} finally {
			setTesting(false);
		}
	};

	const handleSave = async () => {
		if (busy) return;
		setSaveFailed(false);
		setSaving(true);
		try {
			await onSave();
			toast.success(`${title} configuration saved`);
			setIsEditing(false);
			setTestResult(null);
		} catch (error) {
			setSaveFailed(true);
			toast.error("Failed to save configuration", {
				description:
					error instanceof Error ? error.message : "Unknown error",
			});
		} finally {
			setSaving(false);
		}
	};

	const handleDelete = async () => {
		if (busy) return;
		setDeleteFailed(false);
		setSaving(true);
		try {
			await onDelete();
			setRemoved(true);
			setShowDeleteConfirm(false);
			toast.success(`${title} configuration removed`);
			setIsEditing(true);
			setTestResult(null);
		} catch (error) {
			setDeleteFailed(true);
			toast.error("Failed to remove configuration", {
				description:
					error instanceof Error ? error.message : "Unknown error",
			});
		} finally {
			setSaving(false);
		}
	};

	return (
		<>
			<Card>
				<CardHeader>
					<div className="flex flex-wrap items-start justify-between gap-3">
						<div className="flex min-w-0 flex-wrap items-center gap-2">
							{provider === "oidc" ? <Shield className="h-5 w-5" /> : <img src={`/provider-icons/${provider === "microsoft" ? "entra-id.svg" : "google.png"}`} alt="" aria-hidden="true" className="h-5 w-5 object-contain" />}
							<CardTitle ref={headingRef} tabIndex={-1} className="text-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{title}</CardTitle>
							{configured && (
								<Badge
									variant="outline"
									className="bg-[var(--bf-success-soft)] text-[var(--bf-success)] border-transparent"
								>
									<CheckCircle2 className="h-3 w-3 mr-1" />
									Configured
								</Badge>
							)}
						</div>
						{configured && (
							<Button
								variant="ghost"
								size="sm"
								disabled={busy}
								onClick={() => { setRemoved(false); setDeleteFailed(false); setShowDeleteConfirm(true); }}
								className="min-h-11 text-destructive hover:text-destructive"
							>
								<Trash2 className="h-4 w-4 mr-1" />
								Remove
							</Button>
						)}
					</div>
					<CardDescription>{description}</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					{/* Callback URL */}
					<div className="rounded-lg bg-muted/50 p-4">
						<div className="flex items-start justify-between gap-3">
							<div className="min-w-0">
								<p className="text-sm font-medium">
									Callback URL
								</p>
								<p className="text-sm text-muted-foreground mt-1 font-mono [overflow-wrap:anywhere]">
									{callbackUrl}
								</p>
							</div>
							<Button
								variant="ghost"
								size="sm"
								onClick={handleCopyCallback}
								aria-label={`Copy ${title} callback URL`}
								className="size-11 shrink-0"
							>
								<Copy className="h-4 w-4" />
							</Button>
						</div>
					</div>

					{/* Current Configuration (when configured and not editing) */}
					{configured && !isEditing && (
						<div className="space-y-4 border-t pt-4">
							<div className="grid gap-2">
								<div className="grid min-w-0 gap-1 text-sm sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-4">
									<span className="text-muted-foreground">
										Client ID
									</span>
									<span className="min-w-0 font-mono [overflow-wrap:anywhere]">
										{clientId || "Not set"}
									</span>
								</div>
								<div className="grid min-w-0 gap-1 text-sm sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-4">
									<span className="text-muted-foreground">
										Client Secret
									</span>
									<span>
										{clientSecretSet ? (
											<Badge variant="secondary">
												<Key className="h-3 w-3 mr-1" />
												Saved
											</Badge>
										) : (
											"Not set"
										)}
									</span>
								</div>
								{extraFields?.map((field) => (
									<div
										key={field.label}
										className="grid min-w-0 gap-1 text-sm sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-4"
									>
										<span className="text-muted-foreground">
											{field.label}
										</span>
										<span className="min-w-0 font-mono [overflow-wrap:anywhere]">
											{field.value || "Not set"}
										</span>
									</div>
								))}
							</div>
							<div className="flex flex-wrap gap-2 pt-2 [&>button]:min-h-11">
								<Button
									variant="outline"
									size="sm"
									disabled={busy}
									onClick={() => { setSaveFailed(false); onEdit(); setIsEditing(true); }}
								>
									Edit
								</Button>
								<Button
									variant="secondary"
									size="sm"
									onClick={handleTest}
									disabled={busy}
								>
									{testing ? (
										<>
											<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
											Testing...
										</>
									) : testResult?.success ? (
										<>
											<CheckCircle2 className="h-4 w-4 mr-2 text-[var(--bf-success)]" />
											Connected
										</>
									) : testResult?.success === false ? (
										<>
											<AlertCircle className="h-4 w-4 mr-2 text-destructive" />
											Failed
										</>
									) : (
										"Test Connection"
									)}
								</Button>
							</div>
							{testResult && !testResult.success && (
								<p className="text-sm text-destructive mt-2">
									{testResult.message}
								</p>
							)}
						</div>
					)}

					{/* Edit Form */}
					{isEditing && (
						<div className="space-y-4">
							<fieldset disabled={saving} className="min-w-0 space-y-4 [&_input]:min-h-11">{children}</fieldset>
							{saveFailed && <p role="alert" className="text-sm text-destructive">Could not save configuration. Your changes are still here. Try again.</p>}
							<div className="flex flex-wrap gap-2 pt-2 [&>button]:min-h-11">
								{configured && (
									<Button
										variant="outline"
										disabled={saving}
										onClick={() => {
											setIsEditing(false);
											onCancel();
											setTestResult(null);
										}}
									>
										Cancel
									</Button>
								)}
								<Button onClick={handleSave} disabled={saving}>
									{saving ? (
										<>
											<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
											Saving...
										</>
									) : (
										"Save Configuration"
									)}
								</Button>
							</div>
						</div>
					)}
				</CardContent>
			</Card>

			{/* Delete Confirmation Dialog */}
			<Dialog
				open={showDeleteConfirm}
				onOpenChange={(open) => { if (!saving) setShowDeleteConfirm(open); }}
			>
				<DialogContent {...dialogFocus} onEscapeKeyDown={(event) => { if (saving) event.preventDefault(); }} onPointerDownOutside={(event) => { if (saving) event.preventDefault(); }}>
					<DialogHeader>
						<DialogTitle>Remove {title} Configuration</DialogTitle>
						<DialogDescription>
							Are you sure you want to remove {title} SSO? Users
							will no longer be able to sign in with {title} until
							reconfigured.
						</DialogDescription>
					</DialogHeader>
					{deleteFailed && <p role="alert" className="text-sm text-destructive">Could not remove configuration. Try again.</p>}
					<DialogFooter className="[&>button]:min-h-11">
						<Button
							variant="outline"
							onClick={() => setShowDeleteConfirm(false)}
							disabled={saving}
						>
							Cancel
						</Button>
						<Button
							variant="destructive"
							onClick={handleDelete}
							disabled={saving}
						>
							{saving ? (
								<>
									<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
									Removing...
								</>
							) : (
								"Remove Configuration"
							)}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</>
	);
}
