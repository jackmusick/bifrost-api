/**
 * React Query hooks for secret management
 * All hooks use the centralized api client which handles X-Organization-Id automatically
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { secretsService } from '@/services/secrets'
import type { components } from '@/lib/v1'
type SecretCreateRequest = components['schemas']['SecretCreateRequest']
type SecretUpdateRequest = components['schemas']['SecretUpdateRequest']
import { toast } from 'sonner'
import { useScopeStore } from '@/stores/scopeStore'

export function useSecrets() {
  const orgId = useScopeStore((state) => state.scope.orgId)

  return useQuery({
    queryKey: ['secrets', orgId],
    queryFn: () => secretsService.listSecrets(),
    // Don't use cached data from previous scope
    staleTime: 0,
    // Always refetch when component mounts (navigating to page)
    refetchOnMount: 'always',
    meta: {
      onError: (error: Error) => {
        toast.error('Failed to load secrets', {
          description: error.message,
        })
      },
    },
  })
}

export function useCreateSecret() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SecretCreateRequest) => secretsService.createSecret(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] })
      toast.success('Secret created', {
        description: 'The secret has been successfully created',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to create secret', {
        description: error.message,
      })
    },
  })
}

export function useUpdateSecret() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ secretName, data }: { secretName: string; data: SecretUpdateRequest }) =>
      secretsService.updateSecret(secretName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] })
      toast.success('Secret updated', {
        description: 'The secret has been successfully updated',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to update secret', {
        description: error.message,
      })
    },
  })
}

export function useDeleteSecret() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (secretName: string) => secretsService.deleteSecret(secretName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] })
      toast.success('Secret deleted', {
        description: 'The secret has been successfully deleted',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to delete secret', {
        description: error.message,
      })
    },
  })
}
