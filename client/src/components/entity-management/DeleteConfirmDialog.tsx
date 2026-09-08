import { useEffect, useRef } from "react";
import { AlertTriangle, Loader2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

import { ENTITY_CONFIG, type EntityType } from "./types";

export interface DeleteConfirmEntity {
	id: string;
	name: string;
	entityType: EntityType;
	slug?: string;
}

export interface DeleteConfirmDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	entities: DeleteConfirmEntity[];
	isDeleting: boolean;
	failures?: { entity: { id: string; name: string }; message: string }[];
	onConfirm: () => void;
	onCancel: () => void;
}

export function DeleteConfirmDialog({
	open,
	onOpenChange,
	entities,
	isDeleting,
	failures = [],
	onConfirm,
	onCancel,
}: DeleteConfirmDialogProps) {
	const errorRef = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (failures.length && !isDeleting) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [failures, isDeleting]);
	const label =
		entities.length === 1
			? ENTITY_CONFIG[entities[0].entityType].label.toLowerCase()
			: `${entities.length} entities`;
	const hasApps = entities.some((entity) => entity.entityType === "app");

	return (
		<Dialog
			open={open}
			onOpenChange={(nextOpen) => {
				if (!nextOpen && !isDeleting) {
					onOpenChange(nextOpen);
				}
			}}
		>
			<DialogContent
				className="max-h-[90dvh] max-w-2xl gap-5 overflow-y-auto"
				showCloseButton={!isDeleting}
			>
				<DialogHeader className="gap-3">
					<div className="flex items-start gap-3">
						<div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]">
							<Trash2 aria-hidden="true" className="size-5" />
						</div>
						<div className="min-w-0 space-y-1">
							<DialogTitle className="flex items-center gap-2 text-lg leading-snug">
								<AlertTriangle
									aria-hidden="true"
									className="size-4 shrink-0 text-[var(--bf-danger)]"
								/>
								Confirm delete
							</DialogTitle>
							<DialogDescription className="text-sm leading-6">
								This action cannot be undone for workflows and
								apps. Forms and agents will be deactivated.
							</DialogDescription>
						</div>
					</div>
				</DialogHeader>

				{failures.length > 0 && (
					<div
						ref={errorRef}
						tabIndex={-1}
						role="alert"
						className="rounded-[var(--bf-radius-control)] border border-destructive/30 bg-destructive/5 p-3 text-sm outline-none"
					>
						<p className="font-medium text-destructive">
							Some items could not be deleted
						</p>
						<p className="mt-1 text-muted-foreground">
							Completed deletions will not be repeated. Retry the
							remaining items below.
						</p>
						<ul className="mt-3 space-y-2">
							{failures.map(({ entity, message }) => (
								<li
									key={entity.id}
									className="[overflow-wrap:anywhere]"
								>
									<span className="font-medium">
										{entity.name}:{" "}
									</span>
									{message}
								</li>
							))}
						</ul>
					</div>
				)}
				<div className="space-y-4">
					<div className="max-h-[min(50vh,20rem)] overflow-y-auto rounded-[var(--bf-radius-surface)] border border-border bg-card">
						<ul className="divide-y divide-border/70">
							{entities.map((entity) => {
								const config = ENTITY_CONFIG[entity.entityType];
								const Icon = config.icon;
								return (
									<li
										key={entity.id}
										className="flex min-w-0 flex-col items-start gap-2 p-3 sm:flex-row sm:gap-3 sm:p-4"
									>
										<Badge
											variant="outline"
											className="mt-0.5 shrink-0 border-border/70 bg-muted/60 text-muted-foreground"
										>
											<span className="inline-flex items-center gap-1.5">
												<Icon
													aria-hidden="true"
													className="size-3.5"
												/>
												{config.label}
											</span>
										</Badge>
										<div className="min-w-0 flex-1">
											<p className="text-sm font-medium text-foreground [overflow-wrap:anywhere]">
												{entity.name}
											</p>
											<p className="mt-0.5 text-xs text-muted-foreground [overflow-wrap:anywhere]">
												{entity.slug
													? `Slug: ${entity.slug}`
													: "Selected for deletion"}
											</p>
										</div>
									</li>
								);
							})}
						</ul>
					</div>

					{hasApps ? (
						<div className="rounded-[var(--bf-radius-surface)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] px-4 py-3 text-sm text-[var(--bf-warning)]">
							Apps will be permanently deleted.
						</div>
					) : null}
				</div>

				<div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
					<Button
						type="button"
						variant="outline"
						size="lg"
						className="h-auto min-h-11 w-full min-w-0 whitespace-normal sm:w-auto"
						onClick={onCancel}
						disabled={isDeleting}
					>
						Cancel
					</Button>
					<Button
						type="button"
						variant="destructive"
						size="lg"
						className="h-auto min-h-11 w-full min-w-0 whitespace-normal sm:w-auto"
						onClick={onConfirm}
						disabled={isDeleting}
					>
						{isDeleting ? (
							<Loader2
								aria-hidden="true"
								className="size-4 animate-spin motion-reduce:animate-none"
							/>
						) : null}
						<span className="[overflow-wrap:anywhere]">
							{failures.length
								? "Retry deletion"
								: `Delete ${label}`}
						</span>
					</Button>
				</div>
			</DialogContent>
		</Dialog>
	);
}
