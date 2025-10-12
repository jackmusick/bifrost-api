/**
 * React Query hooks for workflows
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { workflowsService } from '@/services/workflows'
import type { WorkflowExecutionRequest } from '@/types/workflow'
import { toast } from 'sonner'

export function useWorkflowsMetadata() {
  return useQuery({
    queryKey: ['workflows', 'metadata'],
    queryFn: () => workflowsService.getMetadata(),
    staleTime: 5 * 60 * 1000, // 5 minutes - workflows don't change often
  })
}

export function useExecuteWorkflow() {
  return useMutation({
    mutationFn: (request: WorkflowExecutionRequest) =>
      workflowsService.executeWorkflow(request),
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
