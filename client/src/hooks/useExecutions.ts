/**
 * React Query hooks for workflow executions
 */

import { useQuery } from '@tanstack/react-query'
import { executionsService } from '@/services/executions'
import type { ExecutionFilters } from '@/types/execution'
import { useScopeStore } from '@/stores/scopeStore'

export function useExecutions(filters?: ExecutionFilters) {
  const orgId = useScopeStore((state) => state.scope.orgId)
  const hasHydrated = useScopeStore((state) => state._hasHydrated)

  // Debug: log when orgId changes
  console.log('useExecutions - orgId:', orgId, 'filters:', filters, 'hasHydrated:', hasHydrated)

  return useQuery({
    queryKey: ['executions', orgId, filters],
    queryFn: () => {
      console.log('useExecutions - queryFn executing for orgId:', orgId)
      // orgId is sent via X-Organization-Id header (handled by api.ts from sessionStorage)
      // We include orgId in the key so React Query automatically refetches when scope changes
      return executionsService.getExecutions(filters)
    },
    // Wait for Zustand to rehydrate from localStorage before making API calls
    enabled: hasHydrated,
    // Show loading state immediately when scope changes (don't show stale data)
    placeholderData: undefined,
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
