import { useMemo, useRef, useState } from "react";
import { Building2, Shield } from "lucide-react";

import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

import { isEntityManaged, formatEntityAccess } from "./types";
import type { EntityWithScope, Organization, Role } from "./types";

const NO_CHANGE = "__no_change__";
const ACCESS_AUTHENTICATED = "authenticated";
const ACCESS_CLEAR_ROLES = "clear-roles";

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

type ChangeDraft = {
	organizationId: string | null | typeof NO_CHANGE;
	accessTarget: string;
};

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
	const [draft, setDraft] = useState<ChangeDraft>({
		organizationId: NO_CHANGE,
		accessTarget: NO_CHANGE,
	});
	const [submitSnapshot, setSubmitSnapshot] = useState<
		EntityWithScope[] | null
	>(null);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const submitting = useRef(false);

	const selected = useMemo(
		() =>
			entities.filter(
				(entity) =>
					selectedIds.has(entity.key) && !isEntityManaged(entity),
			),
		[entities, selectedIds],
	);
	const reviewEntities = submitSnapshot ?? selected;
	const hasDraft =
		draft.organizationId !== NO_CHANGE || draft.accessTarget !== NO_CHANGE;
	const canApply = selected.length > 0 && hasDraft && !disabled && !pending;

	const confirm = async () => {
		if (!canApply || submitting.current) return;
		submitting.current = true;
		setPending(true);
		setError(null);
		const snapshot = selected;
		setSubmitSnapshot(snapshot);
		try {
			if (draft.organizationId !== NO_CHANGE) {
				await onOrganization(
					snapshot.map((entity) => entity.key),
					draft.organizationId,
				);
			}
			if (draft.accessTarget !== NO_CHANGE) {
				await onAccess(
					snapshot.map((entity) => entity.key),
					draft.accessTarget,
				);
			}
			setDraft({ organizationId: NO_CHANGE, accessTarget: NO_CHANGE });
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: "Could not apply changes. Try again.",
			);
		} finally {
			submitting.current = false;
			setPending(false);
			setSubmitSnapshot(null);
		}
	};

	return (
		<section
			aria-label="Entity assignment"
			className="flex min-w-0 flex-col gap-5"
		>
			{!hideInstructions ? (
				<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
					Choose scope, access, or both. Review the exact changes
					before applying them.
				</p>
			) : null}

			<div className="grid gap-4">
				<div className="grid gap-2">
					<Label className="flex items-center gap-2">
						<Building2 className="size-4 text-muted-foreground" />
						Organization
					</Label>
					<div className="grid gap-2 sm:grid-cols-[9rem_minmax(0,1fr)]">
						<Select
							value={
								draft.organizationId === NO_CHANGE
									? NO_CHANGE
									: "change"
							}
							onValueChange={(value) =>
								setDraft((current) => ({
									...current,
									organizationId:
										value === NO_CHANGE ? NO_CHANGE : null,
								}))
							}
							disabled={disabled || pending}
						>
							<SelectTrigger
								aria-label="Organization change mode"
								className="min-h-11 w-full"
							>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value={NO_CHANGE}>
									No change
								</SelectItem>
								<SelectItem value="change">
									Set scope
								</SelectItem>
							</SelectContent>
						</Select>
						<OrganizationSelect
							value={
								draft.organizationId === NO_CHANGE
									? null
									: draft.organizationId
							}
							onChange={(value) =>
								setDraft((current) => ({
									...current,
									organizationId: value ?? null,
								}))
							}
							disabled={
								disabled ||
								pending ||
								draft.organizationId === NO_CHANGE
							}
							showGlobal
							placeholder="Select organization..."
						/>
					</div>
				</div>

				<div className="grid gap-2">
					<Label className="flex items-center gap-2">
						<Shield className="size-4 text-muted-foreground" />
						Access
					</Label>
					<Select
						value={draft.accessTarget}
						onValueChange={(value) =>
							setDraft((current) => ({
								...current,
								accessTarget: value,
							}))
						}
						disabled={disabled || pending}
					>
						<SelectTrigger
							aria-label="Access change"
							className="min-h-11 w-full"
						>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value={NO_CHANGE}>No change</SelectItem>
							<SelectItem value={ACCESS_AUTHENTICATED}>
								Everyone except external users
							</SelectItem>
							<SelectItem value={ACCESS_CLEAR_ROLES}>
								Restricted to roles, clear roles
							</SelectItem>
							{roles.map((role) => (
								<SelectItem key={role.id} value={role.id}>
									Add role: {role.name}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>
			</div>

			<div className="grid gap-3 border-t border-border pt-5">
				<div>
					<h3 className="text-sm font-semibold">Review changes</h3>
					<p className="text-sm text-muted-foreground">
						Compare current and new settings for each selected
						resource.
					</p>
				</div>
				<ul aria-label="Entities to update" className="space-y-2">
					{reviewEntities.length ? (
						reviewEntities.map((entity) => (
							<li
								key={`${entity.entityType}:${entity.id}`}
								className="grid gap-2 rounded-[var(--bf-radius-surface)] border border-border bg-card p-3 text-sm"
							>
								<div className="flex min-w-0 flex-wrap items-center gap-2">
									<span className="min-w-0 font-medium [overflow-wrap:anywhere]">
										{entity.name}
									</span>
									<span className="text-xs capitalize text-muted-foreground">
										{entity.entityType}
									</span>
								</div>
								<ChangeLine
									label="Scope"
									current={scopeName(
										entity.organizationId,
										organizations,
									)}
									proposed={
										draft.organizationId === NO_CHANGE
											? null
											: scopeName(
													draft.organizationId,
													organizations,
												)
									}
								/>
								<ChangeLine
									label="Access"
									current={accessName(entity, roles)}
									proposed={
										draft.accessTarget === NO_CHANGE
											? null
											: proposedAccessName(
													entity,
													draft.accessTarget,
													roles,
												)
									}
								/>
							</li>
						))
					) : (
						<li className="rounded-[var(--bf-radius-surface)] border border-border bg-muted/20 p-3 text-sm text-muted-foreground">
							Select resources to review changes.
						</li>
					)}
				</ul>
			</div>

			{error ? (
				<p role="alert" className="text-sm text-[var(--bf-danger)]">
					{error}
				</p>
			) : null}

			<div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button
					type="button"
					variant="outline"
					disabled={disabled || pending || !hasDraft}
					onClick={() =>
						setDraft({
							organizationId: NO_CHANGE,
							accessTarget: NO_CHANGE,
						})
					}
				>
					Reset
				</Button>
				<Button
					type="button"
					disabled={!canApply}
					onClick={() => void confirm()}
				>
					{pending ? "Applying..." : "Apply changes"}
				</Button>
			</div>
		</section>
	);
}

function ChangeLine({
	label,
	current,
	proposed,
}: {
	label: string;
	current: string;
	proposed: string | null;
}) {
	const changed = proposed !== null && proposed !== current;
	return (
		<p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
			<span className="font-medium text-foreground">{label}:</span>{" "}
			{proposed === null ? (
				<>No change ({current})</>
			) : changed ? (
				<>
					{current} <span aria-hidden="true">-&gt;</span> {proposed}
				</>
			) : (
				<>No change ({current})</>
			)}
		</p>
	);
}

function scopeName(
	organizationId: string | null,
	organizations: Organization[],
) {
	if (!organizationId) return "Global";
	return (
		organizations.find((organization) => organization.id === organizationId)
			?.name ?? "Unknown organization"
	);
}

function accessName(entity: EntityWithScope, roles: Role[]) {
	if (entity.accessLevel === "role_based" && entity.roleIds.length > 0) {
		return roleNames(entity.roleIds, roles);
	}
	return formatEntityAccess(entity.accessLevel);
}

function accessTargetName(target: string, roles: Role[]) {
	if (target === ACCESS_AUTHENTICATED) {
		return "Everyone except external users";
	}
	if (target === ACCESS_CLEAR_ROLES) {
		return "Restricted to roles, no roles";
	}
	return roles.find((role) => role.id === target)?.name ?? "Unknown role";
}

function proposedAccessName(
	entity: EntityWithScope,
	target: string,
	roles: Role[],
) {
	if (target === ACCESS_AUTHENTICATED || target === ACCESS_CLEAR_ROLES) {
		return accessTargetName(target, roles);
	}
	const roleName = accessTargetName(target, roles);
	const currentRoleNames =
		entity.accessLevel === "role_based" && entity.roleIds.length > 0
			? roleNames(entity.roleIds, roles)
			: "";
	return currentRoleNames
		? `${currentRoleNames}, add ${roleName}`
		: `Add role ${roleName}`;
}

function roleNames(roleIds: string[], roles: Role[]) {
	const names = roleIds.map(
		(roleId) => roles.find((role) => role.id === roleId)?.name ?? roleId,
	);
	return names.join(", ");
}
