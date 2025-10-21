import { useQuery } from '@tanstack/react-query'
import { useHealthStore } from '@/stores/healthStore'

interface ServerHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  service: string
  timestamp?: string
  checks?: Array<{
    service: string
    healthy: boolean
    message: string
    metadata?: Record<string, unknown>
  }>
}

export function useWorkflowEngineHealth() {
  const setHealthStatus = useHealthStore((state) => state.setStatus)

  const query = useQuery({
    queryKey: ['serverHealth'],
    queryFn: async () => {
      setHealthStatus('checking')
      try {
        // Call the unified API health endpoint
        const response = await fetch('/api/health', {
          method: 'GET',
          credentials: 'same-origin',
        })

        if (!response.ok) {
          throw new Error('Server health check failed')
        }

        const data = await response.json() as ServerHealthResponse
        // Map degraded to healthy for UI purposes (API is still functional)
        setHealthStatus(data.status === 'unhealthy' ? 'unhealthy' : 'healthy')
        return data
      } catch (error) {
        // Return unhealthy status instead of throwing to avoid error boundaries
        setHealthStatus('unhealthy')
        return {
          status: 'unhealthy' as const,
          service: 'Server',
          error: error instanceof Error ? error.message : 'Unknown error'
        }
      }
    },
    // Only run once on mount - no automatic refetching
    refetchInterval: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
    staleTime: Infinity, // Never consider stale - only manual refresh
  })

  return query
}
