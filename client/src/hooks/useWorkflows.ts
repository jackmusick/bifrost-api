/**
 * React Query hooks for workflows
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { workflowsService } from '@/services/workflows'
import { toast } from 'sonner'
import { useScopeStore } from '@/stores/scopeStore'

export function useWorkflowsMetadata() {
  const orgId = useScopeStore((state) => state.scope.orgId)
  const hasHydrated = useScopeStore((state) => state._hasHydrated)

  return useQuery({
    queryKey: ['workflows', 'metadata', orgId],
    queryFn: () => workflowsService.getMetadata(),
    // Wait for Zustand to rehydrate from localStorage before making API calls
    enabled: hasHydrated,
    // Don't use cached data from previous scope
    staleTime: 0,
  })
}

export function useExecuteWorkflow() {
  return useMutation({
    mutationFn: ({ workflowName, inputData }: { workflowName: string; inputData?: Record<string, unknown> }) =>
      workflowsService.executeWorkflow(workflowName, inputData || {}),
    onSuccess: (data) => {
      toast.success('Workflow execution started', {
        description: `Execution ID: ${data.executionId}`,
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to execute workflow', {
        description: error.message,
      })
    },
  })
}
