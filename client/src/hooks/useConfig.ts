/**
 * React Query hooks for config management
 * All hooks use the centralized api client which handles X-Organization-Id automatically
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { configService } from '@/services/config'
import type { components } from '@/lib/v1'
import type { ConfigScope } from '@/lib/client-types'
type SetConfigRequest = components['schemas']['SetConfigRequest']
import { toast } from 'sonner'
import { useScopeStore } from '@/stores/scopeStore'

export function useConfigs(scope: ConfigScope = 'GLOBAL') {
  const currentOrgId = useScopeStore((state) => state.scope.orgId)

  return useQuery({
    queryKey: ['configs', scope, currentOrgId],
    queryFn: () => {
      console.log('[useConfigs] Fetching configs for scope:', scope, 'orgId:', currentOrgId)
      return configService.getConfigs()
    },
    // Don't use cached data from previous scope
    staleTime: 0,
    // Remove from cache immediately when component unmounts
    gcTime: 0,
    // Always refetch when component mounts (navigating to page)
    refetchOnMount: 'always',
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
    mutationFn: ({ key }: { key: string }) =>
      configService.deleteConfig(key),
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
