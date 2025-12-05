/**
 * React Query hooks for roles management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rolesService } from "@/services/roles";
import type { components } from "@/lib/v1";
type RoleCreate = components["schemas"]["RoleCreate"];
type RoleUpdate = components["schemas"]["RoleUpdate"];
type AssignUsersToRoleRequest =
	components["schemas"]["AssignUsersToRoleRequest"];
type AssignFormsToRoleRequest =
	components["schemas"]["AssignFormsToRoleRequest"];
import { toast } from "sonner";
import { useScopeStore } from "@/stores/scopeStore";

export function useRoles() {
	const orgId = useScopeStore((state) => state.scope.orgId);

	return useQuery({
		queryKey: ["roles", orgId],
		queryFn: () => rolesService.getRoles(),
		// Don't use cached data from previous scope
		staleTime: 0,
		// Always refetch when component mounts (navigating to page)
		refetchOnMount: "always",
	});
}

export function useCreateRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (request: RoleCreate) => rolesService.createRole(request),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({ queryKey: ["roles"] });
			toast.success("Role created", {
				description: `Role "${variables.name}" has been created`,
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to create role", {
				description: error.message,
			});
		},
	});
}

export function useUpdateRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			roleId,
			request,
		}: {
			roleId: string;
			request: RoleUpdate;
		}) => rolesService.updateRole(roleId, request),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["roles"] });
			toast.success("Role updated", {
				description: "The role has been updated successfully",
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to update role", {
				description: error.message,
			});
		},
	});
}

export function useDeleteRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (roleId: string) => rolesService.deleteRole(roleId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["roles"] });
			toast.success("Role deleted", {
				description: "The role has been removed",
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to delete role", {
				description: error.message,
			});
		},
	});
}

export function useRoleUsers(roleId: string | undefined) {
	return useQuery({
		queryKey: ["roles", roleId, "users"],
		queryFn: () => rolesService.getRoleUsers(roleId!),
		enabled: !!roleId,
	});
}

export function useAssignUsersToRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			roleId,
			request,
		}: {
			roleId: string;
			request: AssignUsersToRoleRequest;
		}) => rolesService.assignUsersToRole(roleId, request),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({
				queryKey: ["roles", variables.roleId, "users"],
			});
			toast.success("Users assigned", {
				description: `${variables.request.userIds.length} user(s) assigned to role`,
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to assign users", {
				description: error.message,
			});
		},
	});
}

export function useRemoveUserFromRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({ roleId, userId }: { roleId: string; userId: string }) =>
			rolesService.removeUserFromRole(roleId, userId),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({
				queryKey: ["roles", variables.roleId, "users"],
			});
			toast.success("User removed", {
				description: "User has been removed from the role",
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to remove user", {
				description: error.message,
			});
		},
	});
}

export function useRoleForms(roleId: string | undefined) {
	return useQuery({
		queryKey: ["roles", roleId, "forms"],
		queryFn: () => rolesService.getRoleForms(roleId!),
		enabled: !!roleId,
	});
}

export function useAssignFormsToRole() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			roleId,
			request,
		}: {
			roleId: string;
			request: AssignFormsToRoleRequest;
		}) => rolesService.assignFormsToRole(roleId, request),
		onSuccess: (_, variables) => {
			queryClient.invalidateQueries({
				queryKey: ["roles", variables.roleId, "forms"],
			});
			toast.success("Forms assigned", {
				description: `${variables.request.formIds.length} form(s) assigned to role`,
			});
		},
		onError: (error: Error) => {
			toast.error("Failed to assign forms", {
				description: error.message,
			});
		},
	});
}

/**
 * Remove a form from a role
 * NOTE: Not implemented - the endpoint is not available in the API
 */
// export function useRemoveFormFromRole() {
// 	const queryClient = useQueryClient();

// 	return useMutation({
// 		mutationFn: ({ roleId, formId }: { roleId: string; formId: string }) =>
// 			rolesService.removeFormFromRole(roleId, formId),
// 		onSuccess: (_, variables) => {
// 			queryClient.invalidateQueries({
// 				queryKey: ["roles", variables.roleId, "forms"],
// 			});
// 			toast.success("Form removed", {
// 				description: "Form has been removed from the role",
// 			});
// 		},
// 		onError: (error: Error) => {
// 			toast.error("Failed to remove form", {
// 				description: error.message,
// 			});
// 		},
// 	});
// }
