/**
 * React Query hooks for workflow executions
 */

import { useQuery } from '@tanstack/react-query'
import { executionsService } from '@/services/executions'
import type { ExecutionFilters } from '@/lib/client-types'
import { useScopeStore } from '@/stores/scopeStore'

export function useExecutions(filters?: ExecutionFilters, continuationToken?: string) {
  const orgId = useScopeStore((state) => state.scope.orgId)

  // Debug: log when orgId changes
  console.log('useExecutions - orgId:', orgId, 'filters:', filters, 'token:', continuationToken)

  return useQuery({
    queryKey: ['executions', orgId, filters, continuationToken],
    queryFn: async () => {
      console.log('useExecutions - queryFn executing for orgId:', orgId)
      // orgId is sent via X-Organization-Id header (handled by api.ts from sessionStorage)
      // We include orgId in the key so React Query automatically refetches when scope changes
      const response = await executionsService.getExecutions(filters, continuationToken)
      // Return full response with pagination support
      return response
    },
    // Cache data for 30 seconds to prevent excessive refetching
    staleTime: 30000,
    // Refetch on mount only if data is stale
    refetchOnMount: true,
    // Don't refetch on window focus - use manual refresh or polling hook instead
    refetchOnWindowFocus: false,
  })
}

export function useExecution(executionId: string | undefined) {
  return useQuery({
    queryKey: ['executions', executionId],
    queryFn: () => executionsService.getExecution(executionId!),
    enabled: !!executionId,
    refetchInterval: (query) => {
      // Poll every 10 seconds if status is Pending or Running
      const status = query.state.data?.status
      return status === 'Pending' || status === 'Running' ? 10000 : false
    },
  })
}
