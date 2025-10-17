/**
 * React Query hooks for user management
 */

import { useQuery } from '@tanstack/react-query'
import { usersService } from '@/services/users'

export function useUsers(type?: 'platform' | 'org' | undefined, orgId?: string | undefined) {
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

// Permissions system has been deprecated

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
