/**
 * React Query hooks for secret management
 * All hooks use the centralized api client which handles X-Organization-Id automatically
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { secretsService } from '@/services/secrets'
import type { SecretCreateRequest, SecretUpdateRequest } from '@/types/secret'
import { toast } from 'sonner'

export function useSecrets() {
  return useQuery({
    queryKey: ['secrets'],
    queryFn: () => secretsService.listSecrets(),
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

export function useKeyVaultHealth() {
  return useQuery({
    queryKey: ['health', 'keyvault'],
    queryFn: () => secretsService.getHealthStatus(),
    refetchInterval: 60000, // Refetch every minute
    meta: {
      onError: (error: Error) => {
        toast.error('Failed to check Key Vault health', {
          description: error.message,
        })
      },
    },
  })
}
