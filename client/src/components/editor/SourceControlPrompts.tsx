import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { EntityChange } from "@/hooks/useGitHub";

interface PromptActions {
	disabled: boolean;
	isPending: boolean;
	onConfirm?: (() => void) | undefined;
	onDismiss?: (() => void) | undefined;
}

export function SourceCleanupPrompt({
	count,
	disabled,
	isPending,
	onConfirm,
	onDismiss,
}: PromptActions & { count: number }) {
	return (
		<section
			aria-label="Missing file references"
			className="m-3 space-y-3 rounded-[var(--bf-radius-surface)] border border-border p-3"
		>
			<h4 className="flex items-start gap-2 text-sm font-medium">
				<AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--bf-warning)]" />
				<span>
					{count} missing file reference{count === 1 ? "" : "s"}
				</span>
			</h4>
			<p className="text-sm text-muted-foreground">
				Some entities reference files that no longer exist.
			</p>
			<div className="flex flex-wrap gap-2">
				<Button
					type="button"
					className="min-h-11 h-auto whitespace-normal"
					onClick={onConfirm}
					disabled={disabled || isPending || !onConfirm}
				>
					{isPending && (
						<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
					)}
					{isPending ? "Cleaning up…" : "Clean up and retry"}
				</Button>
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					onClick={onDismiss}
					disabled={disabled || isPending}
				>
					Dismiss
				</Button>
			</div>
		</section>
	);
}

export function SourceDeletionPrompt({
	entities,
	error,
	disabled,
	isPending,
	onConfirm,
	onDismiss,
}: PromptActions & {
	entities: EntityChange[];
	error?: string | null | undefined;
}) {
	return (
		<section
			aria-label="Pending entity deletions"
			className="m-3 min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border border-border p-3"
		>
			<h4 className="flex items-start gap-2 text-sm font-medium">
				<AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
				<span>
					Review {entities.length} pending deletion
					{entities.length === 1 ? "" : "s"}
				</span>
			</h4>
			<p className="text-sm text-muted-foreground">
				Sync will delete these entities because they were removed from
				the repository.
			</p>
			<ul
				aria-label="Entities to delete"
				tabIndex={0}
				className="max-h-64 space-y-3 overflow-y-auto rounded-[var(--bf-radius-control)] border border-border p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				{entities.map((entity, index) => (
					<li
						key={`${entity.entity_type}-${entity.path ?? entity.name}-${index}`}
						className="space-y-1 [overflow-wrap:anywhere]"
					>
						<p className="text-sm font-medium">{entity.name}</p>
						<p className="text-xs text-muted-foreground">
							{entity.entity_type.replaceAll("_", " ")}
						</p>
						{entity.path && (
							<p className="font-mono text-xs text-muted-foreground">
								{entity.path}
							</p>
						)}
					</li>
				))}
			</ul>
			{error && (
				<p
					role="alert"
					className="text-sm text-destructive [overflow-wrap:anywhere]"
				>
					Sync failed: {error}
				</p>
			)}
			{isPending && (
				<p role="status" className="text-sm text-muted-foreground">
					Deleting entities and syncing…
				</p>
			)}
			<div className="flex flex-wrap gap-2">
				<Button
					type="button"
					variant="destructive"
					className="min-h-11 h-auto whitespace-normal"
					onClick={onConfirm}
					disabled={disabled || isPending || !onConfirm}
				>
					{isPending && (
						<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
					)}
					{isPending ? "Deleting and syncing…" : "Delete and sync"}
				</Button>
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					onClick={onDismiss}
					disabled={disabled || isPending}
				>
					Dismiss
				</Button>
			</div>
		</section>
	);
}
