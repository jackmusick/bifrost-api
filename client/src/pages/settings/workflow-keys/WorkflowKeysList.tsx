import {
	AlertTriangle,
	Globe,
	Plus,
	Trash2,
	Workflow as WorkflowIcon,
	Key,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { WorkflowKeyResponse } from "@/services/workflowKeys";
import type { components } from "@/lib/v1";

type WorkflowMetadata = components["schemas"]["WorkflowMetadata"];

export function WorkflowKeysList({
	keys,
	workflowLookup,
	canResolveOrphans,
	canMutate,
	onCreate,
	onRevoke,
}: {
	keys: WorkflowKeyResponse[];
	workflowLookup: Map<string, WorkflowMetadata>;
	canResolveOrphans: boolean;
	canMutate: boolean;
	onCreate: () => void;
	onRevoke: (key: WorkflowKeyResponse, trigger: HTMLButtonElement) => void;
}) {
	if (keys.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center rounded-[var(--bf-radius-surface)] border border-dashed border-border/60 bg-muted/20 py-16 text-center">
				<Key className="h-12 w-12 text-muted-foreground" />
				<h3 className="mt-4 font-display text-lg font-semibold tracking-tight">
					No API keys found
				</h3>
				<p className="mt-2 max-w-sm text-pretty text-sm text-muted-foreground">
					Create your first API key to enable HTTP access to workflows
				</p>
				<Button
					variant="outline"
					size="icon"
					className="mt-4 h-11 w-11 rounded-[var(--bf-radius-control)]"
					onClick={onCreate}
					disabled={!canMutate}
					title="Create API Key"
					aria-label="Create API key"
				>
					<Plus className="h-4 w-4" />
				</Button>
			</div>
		);
	}

	return (
		<div className="flex-1 space-y-3 overflow-auto pr-1 pb-1">
			{keys.map((key) => {
				const expired = isExpired(key.expires_at);
				const workflow = key.workflow_id
					? workflowLookup.get(key.workflow_id)
					: null;
				const isOrphaned =
					Boolean(key.workflow_id) &&
					canResolveOrphans &&
					!workflow;
				const badgeLabel = !key.workflow_id
					? "Global"
					: workflow?.name || key.workflow_name || "Workflow unavailable";

				return (
					<Card
						key={key.id}
						data-testid={`workflow-key-${key.id}`}
						className={cn(
							"overflow-hidden rounded-[var(--bf-radius-surface)]",
							isOrphaned || expired
								? "border-destructive/30 bg-destructive/5"
								: "border-border/70",
						)}
					>
						<CardContent className="p-0">
							<div className="flex flex-col gap-3 p-4 sm:p-5 lg:flex-row lg:items-start lg:justify-between">
								<div className="min-w-0 flex-1 space-y-3">
									<div className="flex flex-wrap items-center gap-2">
										{!key.workflow_id ? (
											<Badge
												variant="default"
												className="shrink-0 text-xs font-semibold"
											>
												<Globe className="mr-1 h-3 w-3" />
												Global
											</Badge>
										) : isOrphaned ? (
											<Badge
												variant="destructive"
												className="h-auto min-w-0 items-start whitespace-normal py-1 [overflow-wrap:anywhere] font-mono text-xs"
											>
												<AlertTriangle className="mr-1 mt-0.5 h-3 w-3 shrink-0" />
												{badgeLabel}
											</Badge>
										) : (
											<Badge
												variant="outline"
												className="h-auto min-w-0 items-start whitespace-normal py-1 [overflow-wrap:anywhere] font-mono text-xs"
											>
												<WorkflowIcon className="mr-1 mt-0.5 h-3 w-3 shrink-0" />
												{badgeLabel}
											</Badge>
										)}
										<span className="min-w-0 text-pretty text-sm text-foreground/90">
											{key.description || (
												<span className="italic text-muted-foreground">
													No description
												</span>
											)}
										</span>
									</div>

									{isOrphaned && (
										<p className="text-xs text-destructive">
											Warning: Workflow no longer exists
										</p>
									)}

									<div className="flex flex-col gap-2 border-t border-border/50 pt-3 sm:flex-row sm:items-center sm:justify-between">
										<code className="min-w-0 break-all rounded-[var(--bf-radius-control)] bg-muted px-2.5 py-1.5 font-mono text-xs text-muted-foreground sm:text-sm">
											{key.masked_key}
										</code>
										<div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground sm:justify-end">
											<span>
												Created {formatRelativeDate(key.created_at)}
											</span>
											{key.last_used_at && (
												<span>
													Used{" "}
													{formatRelativeDate(
														key.last_used_at,
													)}
												</span>
											)}
											{key.expires_at ? (
												expired ? (
													<Badge
														variant="destructive"
														className="text-xs"
													>
														Expired
													</Badge>
												) : (
													<span>
														Expires{" "}
														{formatShortDate(
															key.expires_at,
														)}
													</span>
												)
											) : (
												<span className="text-muted-foreground">
													Never expires
												</span>
											)}
										</div>
									</div>
								</div>

								<Button
									variant="ghost"
									size="icon"
									className="h-11 w-11 shrink-0 rounded-[var(--bf-radius-control)] lg:h-8 lg:w-8"
									onClick={(event) =>
										onRevoke(
											key,
											event.currentTarget as HTMLButtonElement,
										)
									}
									disabled={!canMutate}
									title="Revoke key"
									aria-label={`Revoke key ${key.masked_key}`}
								>
									<Trash2 className="h-4 w-4" />
								</Button>
							</div>
						</CardContent>
					</Card>
				);
			})}
		</div>
	);
}

function formatShortDate(dateString?: string | null) {
	if (!dateString) return "-";
	const date = new Date(dateString);
	return date.toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
	});
}

function formatRelativeDate(dateString?: string | null) {
	if (!dateString) return "-";
	const date = new Date(dateString);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

	if (diffDays === 0) return "Today";
	if (diffDays === 1) return "Yesterday";
	if (diffDays < 7) return `${diffDays} days ago`;
	if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
	return formatShortDate(dateString);
}

function isExpired(expiresAt?: string | null) {
	if (!expiresAt) return false;
	return new Date(expiresAt) < new Date();
}
