/**
 * React Query hooks for config management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { configService } from '@/services/config'
import type { SetConfigRequest, ConfigScope } from '@/types/config'
import { toast } from 'sonner'

export function useConfigs(scope: ConfigScope = 'GLOBAL', orgId?: string | undefined) {
  return useQuery({
    queryKey: ['configs', scope, orgId],
    queryFn: () => configService.getConfigs({
      scope: scope === 'GLOBAL' ? 'global' : scope,
      ...(orgId !== undefined ? { orgId } : {})
    }),
  })
}

export function useSetConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: SetConfigRequest) => configService.setConfig(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      toast.success('Configuration saved', {
        description: `Config key "${variables.key}" has been updated`,
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to save configuration', {
        description: error.message,
      })
    },
  })
}

export function useDeleteConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ key, scope, orgId }: { key: string; scope?: ConfigScope | undefined; orgId?: string | null }) =>
      configService.deleteConfig(key, {
        ...(scope !== undefined ? { scope: scope === 'GLOBAL' ? 'global' : scope } : {}),
        ...(orgId !== undefined && orgId !== null ? { orgId } : {})
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      toast.success('Configuration deleted', {
        description: `Config key "${variables.key}" has been removed`,
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to delete configuration', {
        description: error.message,
      })
    },
  })
}
