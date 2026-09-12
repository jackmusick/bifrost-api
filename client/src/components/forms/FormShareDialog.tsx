import { FormConfirmationEditor } from "./FormConfirmationEditor";
import { FormPublicationReviewDialog, type PublicAction } from "./FormPublicationReviewDialog";
import { FormSharingToggle } from "./FormSharingToggle";
import { FormWebsiteRestrictions } from "./FormWebsiteRestrictions";
import { FormEmbedOptions, type EmbedTheme } from "./FormEmbedOptions";
import { FormEmbedCodePanel } from "./FormEmbedCodePanel";
import { FormPrivateLinkPanel } from "./FormPrivateLinkPanel";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	AlertTriangle,
	RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FormEmbedSection } from "@/components/forms/FormEmbedSection";
import { authFetch } from "@/lib/api-client";
import type { components } from "@/lib/v1";

type FormPublication = components["schemas"]["FormPublicationPublic"];
type PublicationReview = components["schemas"]["FormPublicationReview"];
type FormPublic = components["schemas"]["FormPublic"];

interface FormShareDialogProps {
	formId: string;
	formName: string;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

type RestrictionSaveState = "idle" | "saving" | "saved" | "error";
const DEFAULT_CONFIRMATION_MARKDOWN = "## Form submitted\n\nThank you!";

function parseAllowedOrigins(value: string): string[] {
	return value
		.split(/[\n,]/)
		.map((origin) => origin.trim())
		.filter(Boolean);
}

export function FormShareDialog(props: FormShareDialogProps) {
	// Sharing drafts, request guards and one-time secrets belong to one form.
	return <FormShareDialogSession key={props.formId} {...props} />;
}

function FormShareDialogSession({
	formId,
	formName,
	open,
	onOpenChange,
}: FormShareDialogProps) {
	const [publication, setPublication] = useState<FormPublication | null>(
		null,
	);
	const [review, setReview] = useState<PublicationReview | null>(null);
	const [allowedOrigins, setAllowedOrigins] = useState("");
	const [savedAllowedOrigins, setSavedAllowedOrigins] = useState("");
	const savedOriginsRef = useRef("");
	const originEditVersion = useRef(0);
	const sessionActive = useRef(true);
	useEffect(() => { sessionActive.current = true; return () => { sessionActive.current = false; }; }, []);
	const [restrictionSaveState, setRestrictionSaveState] =
		useState<RestrictionSaveState>("idle");
	const [isLoading, setIsLoading] = useState(false);
	const [loadError, setLoadError] = useState(false);
	const [publicAction, setPublicAction] = useState<PublicAction>(null);
	const [isUpdating, setIsUpdating] = useState(false);
	const [hmacBusy, setHmacBusy] = useState(false);
	const [sharingTab, setSharingTab] = useState("private");
	const [restrictionRetryFocus, setRestrictionRetryFocus] = useState(0);
	const [confirmationMarkdown, setConfirmationMarkdown] = useState(
		DEFAULT_CONFIRMATION_MARKDOWN,
	);
	const [savedConfirmationMarkdown, setSavedConfirmationMarkdown] = useState(
		DEFAULT_CONFIRMATION_MARKDOWN,
	);
	const savedConfirmationRef = useRef(DEFAULT_CONFIRMATION_MARKDOWN);
	const [isSavingConfirmation, setIsSavingConfirmation] = useState(false);
	const [confirmationError, setConfirmationError] = useState(false);
	const confirmationPending = useRef(false);
	const [confirmationView, setConfirmationView] = useState<
		"edit" | "preview"
	>("edit");
	const [spamProtectionEnabled, setSpamProtectionEnabled] = useState(true);
	const [isSavingSpamProtection, setIsSavingSpamProtection] = useState(false);
	const [restrictionsOpen, setRestrictionsOpen] = useState(false);
	const publicationPending = useRef(false);
	const publicationBusy = isUpdating || isSavingSpamProtection || restrictionSaveState === "saving";
	const [embedTheme, setEmbedTheme] = useState<EmbedTheme>("light");
	const [embedHeaderVisible, setEmbedHeaderVisible] = useState(true);
	const [embedTransparent, setEmbedTransparent] = useState(false);
	const [copiedTarget, setCopiedTarget] = useState<
		"private" | "embed" | null
	>(null);

	const privateUrl = `${window.location.origin}/execute/${formId}`;
	const publicIframeSnippet = useMemo(() => {
		if (publication?.status !== "published" || !publication.iframe_path) {
			return "";
		}
		const appearanceParameters = new URLSearchParams({
			theme: embedTheme,
			header: String(embedHeaderVisible),
			background: embedTransparent ? "transparent" : "solid",
		});
		return `<iframe
  src="${window.location.origin}${publication.iframe_path}?${appearanceParameters.toString()}"
  title="${formName.replaceAll('"', "&quot;")}"
  loading="lazy"
  style="width:100%;min-height:640px;border:0"
  sandbox="allow-forms allow-scripts allow-same-origin"
></iframe>`;
	}, [
		embedHeaderVisible,
		embedTheme,
		embedTransparent,
		formName,
		publication,
	]);

	const fetchPublication = useCallback(async () => {
		const savedConfirmationAtRequest = savedConfirmationRef.current;
		const savedOriginsAtRequest = savedOriginsRef.current;
		setIsLoading(true);
		setLoadError(false);
		try {
			const [publicationResponse, reviewResponse, formResponse] =
				await Promise.all([
					authFetch(`/api/forms/${formId}/publication`),
					authFetch(`/api/forms/${formId}/publication-review`),
					authFetch(`/api/forms/${formId}`),
				]);
			if (
				!publicationResponse.ok ||
				!reviewResponse.ok ||
				!formResponse.ok
			) {
				throw new Error("Unable to load sharing settings");
			}
			const nextPublication: FormPublication =
				await publicationResponse.json();
			setPublication(nextPublication);
			setSpamProtectionEnabled(
				nextPublication.spam_protection_enabled ?? true,
			);
			setReview(await reviewResponse.json());
			const formData: FormPublic = await formResponse.json();
			const nextConfirmation =
				formData.confirmation_markdown || DEFAULT_CONFIRMATION_MARKDOWN;
			// A refresh must not discard a draft or supersede a save completed after it started.
			if (savedConfirmationRef.current === savedConfirmationAtRequest) {
				setConfirmationMarkdown(current => current === savedConfirmationAtRequest ? nextConfirmation : current);
				savedConfirmationRef.current = nextConfirmation;
				setSavedConfirmationMarkdown(nextConfirmation);
			}
			const nextAllowedOrigins = (
				nextPublication.allowed_origins || []
			).join("\n");
			if (savedOriginsRef.current === savedOriginsAtRequest) {
				setAllowedOrigins(current => current === savedOriginsAtRequest ? nextAllowedOrigins : current);
				savedOriginsRef.current = nextAllowedOrigins;
				setSavedAllowedOrigins(nextAllowedOrigins);
				setRestrictionSaveState("idle");
			}
			setRestrictionsOpen(current => current || nextAllowedOrigins.length > 0);
		} catch {
			setLoadError(true);
		} finally {
			setIsLoading(false);
		}
	}, [formId]);

	const saveConfirmation = async () => {
		if (confirmationPending.current) return;
		confirmationPending.current = true;
		setConfirmationError(false);
		setIsSavingConfirmation(true);
		try {
			const response = await authFetch(`/api/forms/${formId}`, {
				method: "PATCH",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					confirmation_markdown: confirmationMarkdown,
				}),
			});
			if (!response.ok) throw new Error("Confirmation update failed");
			savedConfirmationRef.current = confirmationMarkdown;
			setSavedConfirmationMarkdown(confirmationMarkdown);
			toast.success("Confirmation Message saved");
		} catch {
			setConfirmationError(true);
		} finally {
			confirmationPending.current = false;
			setIsSavingConfirmation(false);
		}
	};

	useEffect(() => {
		if (!open) return;
		void (async () => {
			await fetchPublication();
		})();
	}, [fetchPublication, open]);

	const handleOpenChange = (nextOpen: boolean) => {
		if (!nextOpen && (hmacBusy || publicationBusy || isSavingConfirmation)) return;
		if (!nextOpen && publication?.status === "published" && allowedOrigins !== savedAllowedOrigins) {
			const version = originEditVersion.current;
			setRestrictionsOpen(true);
			void saveAllowedOrigins(allowedOrigins).then(saved => {
				if (!sessionActive.current) return;
				if (!saved) {
					setSharingTab("website");
					setRestrictionsOpen(true);
					setRestrictionRetryFocus(current => current + 1);
					return;
				}
				if (originEditVersion.current === version) {
					setConfirmationView("edit");
					onOpenChange(false);
				}
			});
			return;
		}
		if (!nextOpen) setConfirmationView("edit");
		onOpenChange(nextOpen);
	};

	const saveAllowedOrigins = useCallback(
		async (nextAllowedOrigins: string) => {
			if (!review || publication?.status !== "published" || publicationPending.current) return false;
			publicationPending.current = true;
			setRestrictionSaveState("saving");
			try {
				const response = await authFetch(
					`/api/forms/${formId}/publication`,
					{
						method: "PUT",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							reviewed_fingerprint: review.fingerprint,
							allowed_origins:
								parseAllowedOrigins(nextAllowedOrigins),
							spam_protection_enabled: spamProtectionEnabled,
						}),
					},
				);
				if (!response.ok) throw new Error("Restriction update failed");
				savedOriginsRef.current = nextAllowedOrigins;
				setSavedAllowedOrigins(nextAllowedOrigins);
				setPublication((current) =>
					current
						? {
								...current,
								allowed_origins:
									parseAllowedOrigins(nextAllowedOrigins),
							}
						: current,
				);
				setRestrictionSaveState("saved");
				return true;
			} catch {
				setRestrictionSaveState("error");
				return false;
			} finally {
				publicationPending.current = false;
			}
		},
		[formId, publication?.status, review, spamProtectionEnabled],
	);

	const saveSpamProtection = async (enabled: boolean) => {
		if (publicationPending.current) return;
		const previous = spamProtectionEnabled;
		setSpamProtectionEnabled(enabled);
		if (!review || publication?.status !== "published") return;

		publicationPending.current = true;
		setIsSavingSpamProtection(true);
		try {
			const response = await authFetch(
				`/api/forms/${formId}/publication`,
				{
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						reviewed_fingerprint: review.fingerprint,
						allowed_origins: parseAllowedOrigins(allowedOrigins),
						spam_protection_enabled: enabled,
					}),
				},
			);
			if (!response.ok) throw new Error("Spam protection update failed");
			const nextPublication: FormPublication = await response.json();
			setPublication(nextPublication);
			savedOriginsRef.current = allowedOrigins;
			setSavedAllowedOrigins(allowedOrigins);
			toast.success(
				enabled
					? "Spam Protection enabled"
					: "Spam Protection disabled",
			);
		} catch {
			setSpamProtectionEnabled(previous);
			toast.error("Could not update Spam Protection");
		} finally {
			publicationPending.current = false;
			setIsSavingSpamProtection(false);
		}
	};

	useEffect(() => {
		if (
			!open ||
			publication?.status !== "published" ||
			allowedOrigins === savedAllowedOrigins ||
			publicationBusy || restrictionSaveState === "error"
		) {
			return;
		}
		const timer = window.setTimeout(() => {
			void saveAllowedOrigins(allowedOrigins);
		}, 700);
		return () => window.clearTimeout(timer);
	}, [
		allowedOrigins,
		open,
		publication?.status,
		saveAllowedOrigins,
		savedAllowedOrigins,
		publicationBusy,
		restrictionSaveState,
	]);

	const copy = async (target: "private" | "embed", value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			setCopiedTarget(target);
			toast.success(
				target === "private"
					? "Private link copied"
					: "Embed code copied",
			);
			window.setTimeout(() => setCopiedTarget(null), 2000);
		} catch {
			toast.error("Could not copy to the clipboard");
		}
	};

	const [publicationError, setPublicationError] = useState(false);
	const updatePublication = async () => {
		if (!review || publicAction !== "publish") return;
		const origins = parseAllowedOrigins(allowedOrigins);
		if (publicationPending.current) return;
		publicationPending.current = true;
		setPublicationError(false);
		setIsUpdating(true);
		try {
			const response = await authFetch(
				`/api/forms/${formId}/publication`,
				{
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						reviewed_fingerprint: review.fingerprint,
						allowed_origins: origins,
						spam_protection_enabled: spamProtectionEnabled,
					}),
				},
			);
			if (!response.ok) throw new Error("Publication failed");
			await fetchPublication();
			setPublicAction(null);
			toast.success("Public embed published");
		} catch {
			setPublicationError(true);
		} finally {
			publicationPending.current = false;
			setIsUpdating(false);
		}
	};

	const rotateOrUnpublish = async () => {
		if (publicAction !== "rotate" && publicAction !== "unpublish") return;
		const rotate = publicAction === "rotate";
		if (publicationPending.current) return;
		publicationPending.current = true;
		setPublicationError(false);
		setIsUpdating(true);
		try {
			const response = await authFetch(
				rotate
					? `/api/forms/${formId}/publication/rotate-key`
					: `/api/forms/${formId}/publication`,
				{ method: rotate ? "POST" : "DELETE" },
			);
			if (!response.ok) throw new Error("Public access update failed");
			await fetchPublication();
			setPublicAction(null);
			toast.success(
				rotate ? "Public embed code rotated" : "Public embed disabled",
			);
		} catch {
			setPublicationError(true);
		} finally {
			publicationPending.current = false;
			setIsUpdating(false);
		}
	};

	const blockers = review?.blockers || [];
	const isPublished = publication?.status === "published";
	const needsReview = publication?.status === "needs_review";

	return (
		<>
			<Dialog open={open} onOpenChange={handleOpenChange}>
				<DialogContent className="max-h-[90dvh] max-w-3xl overflow-x-hidden overflow-y-auto p-[var(--bf-surface-pad)]">
					<DialogHeader className="min-w-0">
						<DialogTitle className="[overflow-wrap:anywhere]">Share {formName}</DialogTitle>
						<DialogDescription>
							Choose how people access this form and what they see
							after submitting it.
						</DialogDescription>
					</DialogHeader>

					<Tabs value={sharingTab} onValueChange={setSharingTab} className="min-w-0">
						<TabsList className="grid w-full grid-cols-3 items-stretch group-data-horizontal/tabs:h-auto">
							<TabsTrigger disabled={hmacBusy || publicationBusy || isSavingConfirmation} value="private" className="h-auto min-h-11 min-w-0 whitespace-normal px-1 text-center leading-5">
								Private Link
							</TabsTrigger>
							<TabsTrigger disabled={hmacBusy || publicationBusy || isSavingConfirmation} value="website" className="h-auto min-h-11 min-w-0 whitespace-normal px-1 text-center leading-5">
								Website Embed
							</TabsTrigger>
							<TabsTrigger disabled={hmacBusy || publicationBusy || isSavingConfirmation} value="hmac" className="h-auto min-h-11 min-w-0 whitespace-normal px-1 text-center leading-5">HMAC</TabsTrigger>
						</TabsList>

						<TabsContent value="private" className="pt-3">
							<FormPrivateLinkPanel url={privateUrl} copied={copiedTarget === "private"} onCopy={() => void copy("private", privateUrl)} />
						</TabsContent>

						<TabsContent value="website" className="pt-3">
							<section className="min-w-0 space-y-4">
								<FormSharingToggle title="Website Embed" label={needsReview ? "Review Required" : isPublished ? "Published" : "Not Published"} description="Anonymous visitors can submit this form without a Bifrost account." checked={isPublished} disabled={isLoading || loadError || publicationBusy || (!isPublished && blockers.length > 0)} onChange={checked => setPublicAction(checked ? "publish" : "unpublish")} />

								{isLoading ? (
									<p className="text-sm text-muted-foreground">
										Loading sharing settings…
									</p>
								) : loadError ? (
									<Alert variant="destructive">
										<AlertTriangle />
										<AlertTitle>
											Sharing settings could not be loaded
										</AlertTitle>
										<AlertDescription>
											<Button
												variant="outline"
												size="sm"
												onClick={() =>
													void fetchPublication()
												}
											>
												<RefreshCw className="h-4 w-4" />{" "}
												Retry
											</Button>
										</AlertDescription>
									</Alert>
								) : (
									<>
										{needsReview ? (
											<Alert variant="destructive">
												<AlertTriangle />
												<AlertTitle>
													The form changed after
													publication
												</AlertTitle>
												<AlertDescription>
													The existing embed is paused
													until its capabilities are
													reviewed and approved again.
												</AlertDescription>
											</Alert>
										) : null}

										<div className="border-t pt-4"><FormSharingToggle title="Spam Protection" label="Spam Protection" description="Require anonymous visitors to complete a private, self-hosted verification. No external service or account is required." checked={spamProtectionEnabled} disabled={publicationBusy} pendingText={isSavingSpamProtection ? "Saving spam protection…" : undefined} onChange={checked => void saveSpamProtection(checked)} /></div>

										<FormWebsiteRestrictions focusRetryRequest={restrictionRetryFocus} open={restrictionsOpen} value={allowedOrigins} published={isPublished} state={restrictionSaveState} onOpenChange={setRestrictionsOpen} busy={publicationBusy} onChange={value => { originEditVersion.current++; setAllowedOrigins(value); setRestrictionSaveState(current => current === "error" ? "idle" : current); }} onRetry={() => void saveAllowedOrigins(allowedOrigins)} />

										{blockers.map((blocker) => (
											<Alert
												key={blocker.code}
												variant="destructive"
											>
												<AlertTriangle />
												<AlertTitle>
													Cannot publish
												</AlertTitle>
												<AlertDescription>
													{blocker.message}
												</AlertDescription>
											</Alert>
										))}

										{isPublished && publicIframeSnippet ? (
											<div className="space-y-3">
												<FormEmbedOptions theme={embedTheme} headerVisible={embedHeaderVisible} transparent={embedTransparent} onTheme={setEmbedTheme} onHeaderVisible={setEmbedHeaderVisible} onTransparent={setEmbedTransparent} />
												<FormEmbedCodePanel code={publicIframeSnippet} />
												<div className="flex justify-end border-t pt-3">
													<Button
														type="button"
														className="min-h-11"
														disabled={publicationBusy}
														variant="outline"
														onClick={() =>
															setPublicAction(
																"rotate",
															)
														}
													>
														Rotate
													</Button>
												</div>
											</div>
										) : null}

										<FormConfirmationEditor value={confirmationMarkdown} savedValue={savedConfirmationMarkdown} view={confirmationView} pending={isSavingConfirmation} error={confirmationError} onView={setConfirmationView} onChange={value => { setConfirmationMarkdown(value); setConfirmationError(false); }} onSave={() => void saveConfirmation()} />
									</>
								)}
							</section>
						</TabsContent>

						<TabsContent value="hmac" className="pt-3">
							<section className="min-w-0">
								<FormEmbedSection formId={formId} onBusyChange={setHmacBusy} />
							</section>
						</TabsContent>
					</Tabs>
				</DialogContent>
			</Dialog>

			<FormPublicationReviewDialog action={publicAction} review={review} pending={publicationBusy} error={publicationError} onClose={() => { if (!publicationPending.current) { setPublicAction(null); setPublicationError(false); } }} onConfirm={() => { if (publicAction === "publish") void updatePublication(); else void rotateOrUnpublish(); }} />
		</>
	);
}
