import { useQuery } from '@tanstack/react-query'

interface WorkflowEngineHealthResponse {
  status: 'healthy' | 'unhealthy'
  service: string
}

export function useWorkflowEngineHealth() {
  return useQuery({
    queryKey: ['workflowEngineHealth'],
    queryFn: async () => {
      try {
        // Call the client API which proxies to workflow engine
        // This goes through /api/workflows/health which is handled by the client API
        const response = await fetch('/api/workflows/health', {
          method: 'GET',
          credentials: 'same-origin',
        })

        if (!response.ok) {
          throw new Error('Workflow engine health check failed')
        }

        return await response.json() as WorkflowEngineHealthResponse
      } catch (error) {
        // Return unhealthy status instead of throwing to avoid error boundaries
        return {
          status: 'unhealthy' as const,
          service: 'Workflow Engine',
          error: error instanceof Error ? error.message : 'Unknown error'
        }
      }
    },
    refetchInterval: 30000, // Check every 30 seconds
    retry: 1,
    staleTime: 10000, // Consider data stale after 10 seconds
  })
}
