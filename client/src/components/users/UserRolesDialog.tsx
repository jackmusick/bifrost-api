import { useRef, useState } from "react";
import { Shield, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useUserRoles } from "@/hooks/useUsers";
import {
	useRoles,
	useAssignUsersToRole,
	useRemoveUserFromRole,
} from "@/hooks/useRoles";
import type { components } from "@/lib/v1";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/api-error";

type User = components["schemas"]["UserPublic"];
type RoleResponse = components["schemas"]["RolePublic"];
type UserRolesResponse = components["schemas"]["UserRolesResponse"];

interface UserRolesDialogProps {
	user: User | undefined;
	open: boolean;
	onClose: () => void;
}

function UserRolesDialogContent({
	user,
	onClose,
}: {
	user: User;
	onClose: () => void;
}) {
	const {
		data: userRoles,
		isLoading: rolesLoading,
		isError: rolesError,
		error: rolesQueryError,
		refetch: refetchRoles,
	} = useUserRoles(user.id);
	const {
		data: allRoles,
		isLoading: allRolesLoading,
		isError: allRolesError,
		error: allRolesQueryError,
		refetch: refetchAllRoles,
	} = useRoles();
	const assignMutation = useAssignUsersToRole();
	const removeMutation = useRemoveUserFromRole();

	const [selectedRoles, setSelectedRoles] = useState<Set<string> | null>(null);
	const [mutationError, setMutationError] = useState<{
		roleId: string;
		roleName: string;
		action: "assign" | "remove";
		message: string;
	} | null>(null);
	const [pendingRoleId, setPendingRoleId] = useState<string | null>(null);
	const mutationInFlight = useRef(false);

	function retryQueryLoad() {
		void Promise.allSettled([refetchRoles(), refetchAllRoles()]);
	}

	function updateSelectedRole(roleId: string, checked: boolean) {
		setSelectedRoles((prev) => {
			const base = prev ?? new Set((userRoles as UserRolesResponse | undefined)?.role_ids ?? []);
			const next = new Set(base);
			if (checked) next.add(roleId);
			else next.delete(roleId);
			return next;
		});
	}

	const selectedRoleIds =
		selectedRoles ?? new Set((userRoles as UserRolesResponse | undefined)?.role_ids ?? []);

	const handleToggleRole = async (
		roleId: string,
		roleName: string,
		checked: boolean,
	) => {
		if (mutationInFlight.current) return;
		const currentlyAssigned = selectedRoleIds.has(roleId);
		if (checked === currentlyAssigned) return;
		mutationInFlight.current = true;
		setPendingRoleId(roleId);
		setMutationError(null);

		try {
			if (checked) {
				await assignMutation.mutateAsync({
					params: { path: { role_id: roleId } },
					body: { user_ids: [user.id] },
				});
				updateSelectedRole(roleId, true);
			} else {
				await removeMutation.mutateAsync({
					params: { path: { role_id: roleId, user_id: user.id } },
				});
				updateSelectedRole(roleId, false);
			}
		} catch (error) {
			const message =
				getErrorMessage(error, "The role could not be updated. Try again.");
			setMutationError({
				roleId,
				roleName,
				action: checked ? "assign" : "remove",
				message,
			});
			toast.error(`Failed to ${checked ? "assign" : "remove"} role`, {
				description: message,
			});
		} finally {
			mutationInFlight.current = false;
			setPendingRoleId(null);
		}
	};

	return (
		<DialogContent
			showCloseButton={false}
			onEscapeKeyDown={(event) => { if (mutationInFlight.current) event.preventDefault(); }}
			onInteractOutside={(event) => { if (mutationInFlight.current) event.preventDefault(); }}
			className="max-h-[calc(100dvh-1rem)] overflow-y-auto sm:max-w-2xl sm:max-h-[calc(100dvh-4rem)]"
		>
			<DialogHeader className="space-y-3">
				<div className="flex items-start gap-3">
					<div className="min-w-0 flex-1 space-y-1">
						<DialogTitle className="flex items-center gap-2 text-balance">
							<Shield className="h-5 w-5 shrink-0" />
							Manage Roles
						</DialogTitle>
						<DialogDescription className="[overflow-wrap:anywhere]">
							Assign or remove roles for {user.name || user.email}.
						</DialogDescription>
					</div>
					<Button
						type="button"
						variant="ghost"
						size="icon-lg"
						disabled={!!pendingRoleId}
						onClick={onClose}
						aria-label="Close dialog"
						className="h-11 w-11 shrink-0 rounded-[var(--bf-radius-control)] border border-border/70 bg-background/90 text-foreground hover:bg-muted motion-reduce:transition-none"
					>
						<X className="h-5 w-5" />
					</Button>
				</div>
			</DialogHeader>

			<div className="space-y-4">
				{user.is_superuser ? (
					<div className="flex items-center justify-center rounded-[var(--bf-radius-surface)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] p-6 text-[var(--bf-warning)]">
						<div className="text-center">
							<Shield className="mx-auto mb-2 h-8 w-8 text-[var(--bf-warning)]" />
							<h3 className="mb-2 font-semibold">
								Cannot Modify Superuser Roles
							</h3>
							<p className="text-sm leading-6 text-[var(--bf-warning)]">
								Superusers have full system access and cannot be assigned
								additional roles.
							</p>
						</div>
					</div>
				) : (
					<>
						{rolesLoading || allRolesLoading ? (
							<div className="space-y-2">
								{[...Array(3)].map((_, i) => (
									<Skeleton key={i} className="h-16 w-full" />
								))}
							</div>
						) : rolesError || allRolesError ? (
							<Alert variant="destructive" className="rounded-[var(--bf-radius-surface)]">
								<AlertTitle>Could not load roles</AlertTitle>
								<AlertDescription className="space-y-3">
									<p className="text-balance">
										{rolesError
											? "User role assignments could not be loaded."
											: "Available roles could not be loaded."}
									</p>
									<div className="flex flex-wrap gap-2">
										<Button
											type="button"
											variant="outline"
											size="sm"
											className="min-h-11"
											onClick={retryQueryLoad}
										>
											Retry
										</Button>
									</div>
									<p className="break-words font-mono text-xs text-muted-foreground">
										{readErrorMessage(rolesQueryError ?? allRolesQueryError)}
									</p>
								</AlertDescription>
							</Alert>
						) : allRoles && allRoles.length > 0 ? (
							<>
								{mutationError ? (
									<Alert variant="destructive" className="rounded-[var(--bf-radius-surface)]">
										<AlertTitle>
											Failed to {mutationError.action} role
										</AlertTitle>
										<AlertDescription className="space-y-3">
											<p className="text-balance">
												{mutationError.roleName} was not updated.
											</p>
											<p className="break-words font-mono text-xs text-muted-foreground">
												{mutationError.message}
											</p>
											<div className="flex flex-wrap gap-2">
												<Button
													type="button"
													variant="outline"
													size="sm"
													className="min-h-11"
													onClick={() =>
														handleToggleRole(
															mutationError.roleId,
															mutationError.roleName,
															mutationError.action === "assign",
														)
													}
													disabled={
														pendingRoleId === mutationError.roleId ||
														assignMutation.isPending ||
														removeMutation.isPending
													}
												>
													Retry
												</Button>
												<Button
													type="button"
													variant="ghost"
													size="sm"
													className="min-h-11"
													onClick={() => setMutationError(null)}
												>
													Dismiss
												</Button>
											</div>
										</AlertDescription>
									</Alert>
								) : null}
								<div className="space-y-3">
									{allRoles.map((role: RoleResponse) => {
										const isAssigned = selectedRoleIds.has(role.id);
										const isPending =
											pendingRoleId === role.id ||
											assignMutation.isPending ||
											removeMutation.isPending;
										return (
											<div
												key={role.id}
												className={cn(
													"flex min-h-14 items-start gap-3 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4 transition-colors motion-reduce:transition-none hover:bg-accent/40",
													isPending && "opacity-70",
												)}
											>
												<Checkbox
													id={role.id}
													checked={isAssigned}
													onCheckedChange={(checked) =>
														handleToggleRole(
															role.id,
															role.name,
															checked === true,
														)
													}
													disabled={isPending}
												/>
												<div className="flex-1 space-y-1">
													<Label
														htmlFor={role.id}
														className="cursor-pointer text-sm font-medium leading-6 text-balance peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
													>
														{role.name}
													</Label>
													{role.description && (
														<p className="break-words text-sm leading-6 text-muted-foreground">
															{role.description}
														</p>
													)}
												</div>
											</div>
										);
									})}
								</div>
							</>
						) : (
							<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 px-4 py-8 text-center text-sm leading-6 text-muted-foreground">
								No roles available
							</div>
						)}
					</>
				)}
			</div>

			<div className="flex justify-end">
				<Button disabled={!!pendingRoleId}
						onClick={onClose} className="min-h-11">
					Close
				</Button>
			</div>
		</DialogContent>
	);
}

function readErrorMessage(error: unknown): string {
	if (error instanceof Error) return error.message;
	if (typeof error === "string") return error;
	return "Unknown query error";
}

export function UserRolesDialog({ user, open, onClose }: UserRolesDialogProps) {
	if (!user) return null;

	return (
		<Dialog open={open} onOpenChange={onClose}>
			{open && <UserRolesDialogContent key={user.id} user={user} onClose={onClose} />}
		</Dialog>
	);
}
