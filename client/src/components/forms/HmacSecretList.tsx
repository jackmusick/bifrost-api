import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

export interface HmacSecretSummary {
	id: string;
	name: string;
	is_active: boolean;
	hmac_scheme: "shopify" | "halopsa";
	created_at: string;
}

export function HmacSecretList({
	secrets,
	loading,
	busy = false,
	error,
	onRetry,
	onToggle,
	onDelete,
}: {
	secrets: HmacSecretSummary[];
	loading: boolean;
	busy?: boolean;
	error: boolean;
	onRetry: () => void;
	onToggle: (secret: HmacSecretSummary) => void;
	onDelete: (secret: HmacSecretSummary) => void;
}) {
	return (
		<section aria-label="HMAC secrets" className="min-w-0 space-y-3">
			{error && (
				<div className="space-y-2 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)]">
					<p role="alert" className="text-sm">
						Embed secrets could not be loaded.
						{secrets.length > 0
							? " Showing the last available records."
							: " Retry to check which secrets are configured."}
					</p>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						disabled={loading || busy}
						onClick={onRetry}
					>
						{loading ? "Retrying…" : "Retry embed secrets"}
					</Button>
				</div>
			)}
			{busy && !loading && (
				<p role="status" className="text-sm text-muted-foreground">
					Updating embed secrets…
				</p>
			)}
			{loading && (
				<p role="status" className="text-sm text-muted-foreground">
					{secrets.length
						? "Refreshing embed secrets…"
						: "Loading embed secrets…"}
				</p>
			)}
			{!loading && !error && !secrets.length && (
				<div className="py-4 text-sm text-muted-foreground">
					<p>No embed secrets configured.</p>
					<p className="mt-1">
						Create a secret to enable iframe embedding.
					</p>
				</div>
			)}
			{secrets.map((secret) => (
				<article
					key={secret.id}
					className="space-y-3 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)]"
				>
					<div className="min-w-0 space-y-1">
						<h4 className="text-sm font-medium [overflow-wrap:anywhere]">
							{secret.name}
						</h4>
						<p className="text-xs text-muted-foreground">
							Created{" "}
							{new Date(secret.created_at).toLocaleDateString()}
						</p>
					</div>
					<div className="flex flex-wrap gap-2">
						<Badge
							variant="outline"
							className={
								secret.is_active
									? "border-transparent bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
									: "text-muted-foreground"
							}
						>
							{secret.is_active ? "Active" : "Inactive"}
						</Badge>
						<Badge variant="outline">
							{secret.hmac_scheme === "halopsa"
								? "HaloPSA"
								: "Standard"}
						</Badge>
					</div>
					<div className="flex flex-wrap items-center gap-2">
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							disabled={loading || busy}
							onClick={() => onToggle(secret)}
						>
							{secret.is_active ? "Deactivate" : "Activate"}
						</Button>
						<RecordActionsMenu
							label={`More actions for ${secret.name}`}
						>
							<DropdownMenuItem
								variant="destructive"
								className="min-h-11"
								disabled={loading || busy}
								onSelect={(event) => {
									event.preventDefault();
									onDelete(secret);
								}}
								aria-label={`Delete ${secret.name}`}
							>
								<Trash2 aria-hidden="true" className="size-4" />
								Delete
							</DropdownMenuItem>
						</RecordActionsMenu>
					</div>
				</article>
			))}
		</section>
	);
}
