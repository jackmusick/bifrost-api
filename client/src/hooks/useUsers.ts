/**
 * React Query hooks for user management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '@/services/users'
import type { GrantPermissionsRequest } from '@/types/user'
import { toast } from 'sonner'

export function useUsers(type?: 'msp' | 'org' | undefined, orgId?: string | undefined) {
  return useQuery({
    queryKey: ['users', type, orgId],
    queryFn: () => usersService.getUsers({
      ...(type !== undefined ? { type } : {}),
      ...(orgId !== undefined ? { orgId } : {})
    }),
  })
}

export function useUser(userId: string | undefined) {
  return useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersService.getUser(userId!),
    enabled: !!userId,
  })
}

export function useUserPermissions(userId: string | undefined, orgId: string | undefined) {
  return useQuery({
    queryKey: ['users', userId, 'permissions', orgId],
    queryFn: () => usersService.getUserPermissions(userId!, orgId!),
    enabled: !!userId && !!orgId,
  })
}

export function useOrgPermissions(orgId: string | undefined) {
  return useQuery({
    queryKey: ['organizations', orgId, 'permissions'],
    queryFn: () => usersService.getOrgPermissions(orgId!),
    enabled: !!orgId,
  })
}

export function useGrantPermissions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: GrantPermissionsRequest) => usersService.grantPermissions(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users', variables.userId, 'permissions'] })
      queryClient.invalidateQueries({ queryKey: ['organizations', variables.orgId, 'permissions'] })
      toast.success('Permissions granted', {
        description: 'User permissions have been updated',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to grant permissions', {
        description: error.message,
      })
    },
  })
}

export function useRevokePermissions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ userId, orgId }: { userId: string; orgId: string }) =>
      usersService.revokePermissions(userId, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users', variables.userId, 'permissions'] })
      queryClient.invalidateQueries({ queryKey: ['organizations', variables.orgId, 'permissions'] })
      toast.success('Permissions revoked', {
        description: 'User permissions have been removed',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to revoke permissions', {
        description: error.message,
      })
    },
  })
}

export function useUserRoles(userId: string | undefined) {
  return useQuery({
    queryKey: ['users', userId, 'roles'],
    queryFn: () => usersService.getUserRoles(userId!),
    enabled: !!userId,
  })
}

export function useUserForms(userId: string | undefined) {
  return useQuery({
    queryKey: ['users', userId, 'forms'],
    queryFn: () => usersService.getUserForms(userId!),
    enabled: !!userId,
  })
}
