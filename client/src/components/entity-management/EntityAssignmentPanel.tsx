import { isEntityManaged } from "./types";
import { useRef, useState, useEffect } from "react";
import { Building2, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

import { OrgDropTarget, RoleDropTarget } from "./DropTargets";
import type { EntityWithScope, Organization, Role } from "./types";

interface Assignment {
	kind: "organization" | "access";
	target: string | null;
	name: string;
	entities: EntityWithScope[];
}

interface EntityAssignmentPanelProps {
	hideInstructions?: boolean;
	entities: EntityWithScope[];
	selectedIds: Set<string>;
	organizations: Organization[];
	roles: Role[];
	disabled: boolean;
	onOrganization: (
		ids: string[],
		organizationId: string | null,
	) => Promise<void>;
	onAccess: (ids: string[], roleOrAccessLevel: string) => Promise<void>;
}

export function EntityAssignmentPanel({
	entities,
	hideInstructions = false,
	selectedIds,
	organizations,
	roles,
	disabled,
	onOrganization,
	onAccess,
}: EntityAssignmentPanelProps) {
	const [assignment, setAssignment] = useState<Assignment | null>(null);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const submitting = useRef(false);
	const errorRef = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		if (error) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [error]);
	const origin = useRef<HTMLElement | null>(null);

	const selected = entities
		.filter(
			(entity) => selectedIds.has(entity.id) && !isEntityManaged(entity),
		)
		.map((entity) => entity.id);

	const choose = (
		kind: Assignment["kind"],
		ids: string[],
		target: string | null,
		name: string,
	) => {
		if (disabled || submitting.current) return;
		const snapshot = entities.filter(
			(entity) => ids.includes(entity.id) && !isEntityManaged(entity),
		);
		if (!snapshot.length) return;
		origin.current =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;
		setError(null);
		setAssignment({ kind, target, name, entities: snapshot });
	};

	const confirm = async () => {
		if (!assignment || disabled || submitting.current) return;
		submitting.current = true;
		setPending(true);
		setError(null);

		try {
			const ids = assignment.entities.map((entity) => entity.id);
			if (assignment.kind === "organization") {
				await onOrganization(ids, assignment.target);
			} else {
				await onAccess(ids, assignment.target!);
			}
			setAssignment(null);
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: "Could not apply changes. Try again.",
			);
		} finally {
			submitting.current = false;
			setPending(false);
		}
	};

	return (
		<section
			aria-label="Entity assignment"
			className="flex min-w-0 flex-col gap-4 lg:min-h-0"
		>
			{!hideInstructions && (
				<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
					Select entities, then choose an organization or access
					setting. You can also drag entities to a destination. Review
					changes before applying them.
				</p>
			)}

			<div className="grid gap-4 xl:grid-cols-2">
				<AssignmentGroup
					title="Organizations"
					icon={
						<Building2
							aria-hidden="true"
							className="size-5 text-muted-foreground"
						/>
					}
					description="Move the selected entities to a different organization."
				>
					<div className="space-y-3">
						{[null, ...organizations].map((organization) => (
							<OrgDropTarget
								key={organization?.id ?? "global"}
								organization={organization}
								selectedIds={selected}
								disabled={disabled || pending}
								onDrop={(ids, target) =>
									choose(
										"organization",
										ids,
										target,
										organization?.name ?? "Global",
									)
								}
							/>
						))}
					</div>
				</AssignmentGroup>

				<AssignmentGroup
					title="Access"
					icon={
						<Shield
							aria-hidden="true"
							className="size-5 text-muted-foreground"
						/>
					}
					description="Apply a role, remove roles, or leave entities authenticated only."
				>
					<div className="space-y-3">
						{(
							["authenticated", "clear-roles", ...roles] as const
						).map((role) => (
							<RoleDropTarget
								key={typeof role === "string" ? role : role.id}
								role={role}
								selectedIds={selected}
								disabled={disabled || pending}
								onDrop={(ids, target) =>
									choose(
										"access",
										ids,
										target,
										role === "authenticated"
											? "Everyone except external users"
											: role === "clear-roles"
												? "Clear roles"
												: role.name,
									)
								}
							/>
						))}
					</div>
				</AssignmentGroup>
			</div>

			<Dialog
				open={!!assignment}
				onOpenChange={(open) => {
					if (!open && !submitting.current) setAssignment(null);
				}}
			>
				<DialogContent
					className="max-h-[90dvh] max-w-2xl gap-5 overflow-y-auto"
					showCloseButton={!pending}
					onCloseAutoFocus={(event) => {
						if (origin.current?.isConnected) {
							event.preventDefault();
							origin.current.focus();
						}
					}}
				>
					<DialogHeader className="gap-2">
						<DialogTitle>
							{assignment?.kind === "organization"
								? "Change organization"
								: "Change access"}
						</DialogTitle>
						<DialogDescription className="[overflow-wrap:anywhere]">
							Apply {assignment?.name} to{" "}
							{assignment?.entities.length}{" "}
							{assignment?.entities.length === 1
								? "entity"
								: "entities"}
							.
						</DialogDescription>
					</DialogHeader>

					{assignment?.target === "clear-roles" ? (
						<div className="rounded-[var(--bf-radius-surface)] border border-border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
							This removes all role assignments and sets access to
							role-based.
						</div>
					) : null}

					<ul
						aria-label="Entities to update"
						tabIndex={0}
						className="max-h-60 space-y-2 overflow-y-auto rounded-[var(--bf-radius-surface)] border border-border bg-card p-[var(--bf-surface-pad)] text-sm focus-visible:outline-2 focus-visible:outline-ring"
					>
						{assignment?.entities.map((entity) => (
							<li
								key={`${entity.entityType}:${entity.id}`}
								className="flex min-w-0 flex-col items-start gap-1 [overflow-wrap:anywhere] sm:flex-row sm:gap-2"
							>
								<span className="min-w-0 font-medium text-foreground">
									{entity.name}
								</span>
								<span className="shrink-0 text-xs text-muted-foreground">
									{entity.entityType}
								</span>
							</li>
						))}
					</ul>

					{error ? (
						<p
							ref={errorRef}
							tabIndex={-1}
							role="alert"
							className="text-sm text-[var(--bf-danger)] [overflow-wrap:anywhere]"
						>
							{error}
						</p>
					) : null}

					{pending ? (
						<p
							role="status"
							className="text-sm text-muted-foreground"
						>
							Applying changes…
						</p>
					) : null}

					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="outline"
							size="lg"
							className="w-full sm:w-auto"
							disabled={pending}
							onClick={() => setAssignment(null)}
						>
							Cancel
						</Button>
						<Button
							type="button"
							size="lg"
							className="w-full sm:w-auto"
							disabled={disabled || pending}
							onClick={() => void confirm()}
						>
							{pending
								? "Applying…"
								: error
									? "Retry changes"
									: "Apply changes"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</section>
	);
}

function AssignmentGroup({
	title,
	icon,
	description,
	children,
}: {
	title: string;
	icon: React.ReactNode;
	description: string;
	children: React.ReactNode;
}) {
	return (
		<section className="rounded-[var(--bf-radius-surface)] border border-border bg-card p-[var(--bf-surface-pad)]">
			<div className="space-y-3">
				<div className="flex items-start gap-3">
					{icon}
					<div className="min-w-0 space-y-1">
						<h2 className="text-base font-semibold leading-snug">
							{title}
						</h2>
						<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
							{description}
						</p>
					</div>
				</div>
				{children}
			</div>
		</section>
	);
}
