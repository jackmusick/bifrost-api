import { useQuery } from '@tanstack/react-query'

interface ServerHealthResponse {
  status: 'healthy' | 'unhealthy'
  service: string
}

export function useWorkflowEngineHealth() {
  return useQuery({
    queryKey: ['serverHealth'],
    queryFn: async () => {
      try {
        // Call the unified API health endpoint
        const response = await fetch('/api/health', {
          method: 'GET',
          credentials: 'same-origin',
        })

        if (!response.ok) {
          throw new Error('Server health check failed')
        }

        return await response.json() as ServerHealthResponse
      } catch (error) {
        // Return unhealthy status instead of throwing to avoid error boundaries
        return {
          status: 'unhealthy' as const,
          service: 'Server',
          error: error instanceof Error ? error.message : 'Unknown error'
        }
      }
    },
    refetchInterval: 30000, // Check every 30 seconds
    retry: 1,
    staleTime: 10000, // Consider data stale after 10 seconds
  })
}
