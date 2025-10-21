/**
 * React Query hooks for workflows
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { workflowsService } from '@/services/workflows'
import { toast } from 'sonner'
import { useScopeStore } from '@/stores/scopeStore'

export function useWorkflowsMetadata() {
  const orgId = useScopeStore((state) => state.scope.orgId)

  return useQuery({
    queryKey: ['workflows', 'metadata', orgId],
    queryFn: () => {
      console.log('[useWorkflowsMetadata] Fetching workflows for orgId:', orgId)
      return workflowsService.getMetadata()
    },
    // Don't use cached data from previous scope
    staleTime: 0,
    // Remove from cache immediately when component unmounts
    gcTime: 0,
    // Always refetch when component mounts (navigating to page)
    refetchOnMount: 'always',
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
