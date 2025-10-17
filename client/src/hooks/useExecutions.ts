/**
 * React Query hooks for workflow executions
 */

import { useQuery } from '@tanstack/react-query'
import { executionsService } from '@/services/executions'
import type { ExecutionFilters } from '@/lib/client-types'
import { useScopeStore } from '@/stores/scopeStore'

export function useExecutions(filters?: ExecutionFilters) {
  const orgId = useScopeStore((state) => state.scope.orgId)

  // Debug: log when orgId changes
  console.log('useExecutions - orgId:', orgId, 'filters:', filters)

  return useQuery({
    queryKey: ['executions', orgId, filters],
    queryFn: () => {
      console.log('useExecutions - queryFn executing for orgId:', orgId)
      // orgId is sent via X-Organization-Id header (handled by api.ts from sessionStorage)
      // We include orgId in the key so React Query automatically refetches when scope changes
      return executionsService.getExecutions(filters)
    },
    // Don't use cached data from previous scope
    staleTime: 0,
  })
}

export function useExecution(executionId: string | undefined) {
  return useQuery({
    queryKey: ['executions', executionId],
    queryFn: () => executionsService.getExecution(executionId!),
    enabled: !!executionId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if status is Pending or Running
      const status = query.state.data?.status
      return status === 'Pending' || status === 'Running' ? 2000 : false
    },
  })
}
