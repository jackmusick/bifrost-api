import { FormEmbedCodePanel } from "./FormEmbedCodePanel";
import { HmacSecretCreateForm, type HmacScheme } from "./HmacSecretCreateForm";
import { HmacSecretDeleteDialog } from "./HmacSecretDeleteDialog";
import { HmacSecretReveal } from "./HmacSecretReveal";
import { HmacSecretList, type HmacSecretSummary } from "./HmacSecretList";
/**
 * Form HMAC Integration Section
 *
 * HMAC sharing tab for trusted systems that sign dynamic embed parameters.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

import { authFetch } from "@/lib/api-client";
import { toast } from "sonner";

// ============================================================================
// Types
// ============================================================================


type EmbedSecret = HmacSecretSummary;

interface EmbedSecretCreated extends EmbedSecret {
	raw_secret: string;
}

interface FormEmbedSectionProps {
	formId: string;
	onBusyChange?: ((busy: boolean) => void) | undefined;
}

// ============================================================================
// Component
// ============================================================================

export function FormEmbedSection({ formId, onBusyChange }: FormEmbedSectionProps) {
	const [secrets, setSecrets] = useState<EmbedSecret[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);

	// Create form state
	const [isCreateOpen, setIsCreateOpen] = useState(false);
	const [createName, setCreateName] = useState("");
	const [createSecret, setCreateSecret] = useState("");
	const [createScheme, setCreateScheme] = useState<HmacScheme>("shopify");
	const [isCreating, setIsCreating] = useState(false);
	const [createError, setCreateError] = useState(false);

	// Reveal state (shown once after creation)
	const [revealedSecret, setRevealedSecret] =
		useState<EmbedSecretCreated | null>(null);

	// Delete confirmation state
	const [deleteTarget, setDeleteTarget] = useState<EmbedSecret | null>(null);
	const [isDeleting, setIsDeleting] = useState(false);
	const [isToggling, setIsToggling] = useState(false);
	const [deleteError, setDeleteError] = useState(false);
	const mutationPending = useRef(false);
	const busy = isCreating || isDeleting || isToggling;
	useEffect(() => { onBusyChange?.(busy); }, [busy, onBusyChange]);
	useEffect(() => () => onBusyChange?.(false), [onBusyChange]);


	// ========================================================================
	// Data fetching
	// ========================================================================

	const fetchSecrets = useCallback(async () => {
		setIsLoading(true);
		try {
			const res = await authFetch(`/api/forms/${formId}/embed-secrets`);
			if (!res.ok) throw new Error("Could not load embed secrets");
			setSecrets(await res.json());
			setLoadError(false);
		} catch {
			setLoadError(true);
		} finally {
			setIsLoading(false);
		}
	}, [formId]);

	useEffect(() => {
		void (async () => {
			await fetchSecrets();
		})();
	}, [fetchSecrets]);

	// ========================================================================
	// Actions
	// ========================================================================

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!createName.trim()) return;

		if (mutationPending.current) return;
		mutationPending.current = true;
		setIsCreating(true);
		setCreateError(false);
		try {
			const res = await authFetch(`/api/forms/${formId}/embed-secrets`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					name: createName.trim(),
					hmac_scheme: createScheme,
					...(createSecret.trim() && { secret: createSecret.trim() }),
				}),
			});
			if (!res.ok) throw new Error(await res.text());
			const created: EmbedSecretCreated = await res.json();
			setRevealedSecret(created);
			setIsCreateOpen(false);
			setCreateName("");
			setCreateSecret("");
			setCreateScheme("shopify");
			fetchSecrets();
			toast.success("Embed secret created");
		} catch {
			setCreateError(true);
		} finally {
			mutationPending.current = false;
			setIsCreating(false);
		}
	};

	const handleToggleActive = async (secret: EmbedSecret) => {
		if (mutationPending.current) return;
		mutationPending.current = true;
		setIsToggling(true);
		try {
			const res = await authFetch(
				`/api/forms/${formId}/embed-secrets/${secret.id}`,
				{
					method: "PATCH",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ is_active: !secret.is_active }),
				},
			);
			if (!res.ok) throw new Error(await res.text());
			fetchSecrets();
			toast.success(
				secret.is_active ? "Secret deactivated" : "Secret activated",
			);
		} catch {
			toast.error("Failed to update secret");
		} finally { mutationPending.current = false; setIsToggling(false); }
	};

	const handleDelete = async () => {
		if (!deleteTarget || mutationPending.current) return;
		mutationPending.current = true;
		setIsDeleting(true);
		setDeleteError(false);
		try {
			const res = await authFetch(
				`/api/forms/${formId}/embed-secrets/${deleteTarget.id}`,
				{ method: "DELETE" },
			);
			if (!res.ok) throw new Error(await res.text());
			setSecrets(current => current.filter(secret => secret.id !== deleteTarget.id));
			setDeleteTarget(null);
			fetchSecrets();
			toast.success("Secret deleted");
		} catch {
			setDeleteError(true);
		} finally { mutationPending.current = false; setIsDeleting(false); }
	};

	// ========================================================================
	// Code snippets
	// ========================================================================

	const embedUrl = `${window.location.origin}/embed/forms/${formId}`;

	const iframeSnippet = `<iframe
  src="${embedUrl}?param1=value1&hmac=COMPUTED_HMAC"
  style="width: 100%; height: 600px; border: none;"
  allow="clipboard-write"
></iframe>`;
	// ========================================================================
	// Render
	// ========================================================================

	return (
		<>
			<div className="space-y-4">
				{/* ============ Secrets ============ */}
				<div className="space-y-3">
					<div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
						<p className="text-sm text-muted-foreground">
							Shared secrets for HMAC-authenticated iframe
							embedding. After submission, the iframe opens the
							execution result for that signed session.
						</p>
						<Button type="button" className="min-h-11 shrink-0" disabled={busy} onClick={() => { setCreateError(false); setIsCreateOpen(true); }}>
							<Plus className="mr-2 h-4 w-4" />
							Create Secret
						</Button>
					</div>

					<HmacSecretList secrets={secrets} loading={isLoading} busy={busy} error={loadError} onRetry={() => void fetchSecrets()} onToggle={secret => void handleToggleActive(secret)} onDelete={secret => { setDeleteError(false); setDeleteTarget(secret); }} />

					{/* Inline create form */}
					{isCreateOpen && (
						<HmacSecretCreateForm name={createName} secret={createSecret} scheme={createScheme} busy={busy} creating={isCreating} error={createError} onName={setCreateName} onSecret={setCreateSecret} onScheme={setCreateScheme} onSubmit={handleCreate} onCancel={() => {
							setIsCreateOpen(false);
							setCreateName("");
							setCreateSecret("");
							setCreateScheme("shopify");
							setCreateError(false);
						}} />
					)}

					{/* One-time secret reveal */}
					{revealedSecret && (
						<HmacSecretReveal key={revealedSecret.id} value={revealedSecret.raw_secret} onDismiss={() => setRevealedSecret(null)} />
					)}
				</div>

				<FormEmbedCodePanel code={iframeSnippet} />
			</div>

			{/* ============ Delete Confirmation ============ */}
			<HmacSecretDeleteDialog name={deleteTarget?.name ?? null} pending={isDeleting} error={deleteError} onClose={() => { if (!mutationPending.current) setDeleteTarget(null); }} onConfirm={() => void handleDelete()} />
		</>
	);
}
