/**
 * React Query hooks for workflow executions
 */

import { useQuery } from '@tanstack/react-query'
import { executionsService } from '@/services/executions'
import type { ExecutionFilters } from '@/types/execution'
import { useUser } from '@/contexts/UserContext'

export function useExecutions(filters?: ExecutionFilters) {
  const { orgId } = useUser()

  return useQuery({
    queryKey: ['executions', orgId, filters],
    queryFn: () => {
      // Note: orgId is sent via X-Organization-Id header (handled by api.ts)
      // No need to pass it as a parameter
      return executionsService.getExecutions(filters)
    },
    // Allow querying even without orgId (for GLOBAL scope)
    refetchInterval: 5000, // Poll every 5 seconds for live updates
  })
}

export function useExecution(executionId: string | undefined) {
  const { orgId } = useUser()

  return useQuery({
    queryKey: ['executions', executionId, orgId],
    queryFn: () => executionsService.getExecution(executionId!),
    enabled: !!executionId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if status is Pending or Running
      const status = query.state.data?.status
      return status === 'Pending' || status === 'Running' ? 2000 : false
    },
  })
}
