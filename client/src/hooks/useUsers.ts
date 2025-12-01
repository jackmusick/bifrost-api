/**
 * React Query hooks for user management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersService } from "@/services/users";
import { useScopeStore } from "@/stores/scopeStore";

export function useUsers() {
	const orgId = useScopeStore((state) => state.scope.orgId);

	return useQuery({
		queryKey: ["users", orgId],
		queryFn: () => {
			// orgId is sent via X-Organization-Id header (handled by api.ts from sessionStorage)
			// We include orgId in the key so React Query automatically refetches when scope changes
			return usersService.getUsers();
		},
		// Don't use cached data from previous scope
		staleTime: 0,
		// Remove from cache immediately when component unmounts
		gcTime: 0,
		// Always refetch when component mounts (navigating to page)
		refetchOnMount: "always",
	});
}

export function useUser(userId: string | undefined) {
	return useQuery({
		queryKey: ["users", userId],
		queryFn: () => usersService.getUser(userId!),
		enabled: !!userId,
	});
}

// Permissions system has been deprecated

export function useUserRoles(userId: string | undefined) {
	return useQuery({
		queryKey: ["users", userId, "roles"],
		queryFn: () => usersService.getUserRoles(userId!),
		enabled: !!userId,
	});
}

export function useUserForms(userId: string | undefined) {
	return useQuery({
		queryKey: ["users", userId, "forms"],
		queryFn: () => usersService.getUserForms(userId!),
		enabled: !!userId,
	});
}

export function useCreateUser() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: usersService.createUser,
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["users"] });
		},
	});
}

export function useUpdateUser() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: ({
			userId,
			body,
		}: {
			userId: string;
			body: Parameters<typeof usersService.updateUser>[1];
		}) => usersService.updateUser(userId, body),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["users"] });
		},
	});
}

export function useDeleteUser() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (userId: string) => usersService.deleteUser(userId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["users"] });
		},
	});
}
