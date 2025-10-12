import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

export interface DashboardMetrics {
  workflowCount: number
  dataProviderCount: number
  formCount: number
  executionStats: {
    totalExecutions: number
    successCount: number
    failedCount: number
    runningCount: number
    pendingCount: number
    successRate: number
    avgDurationSeconds: number
  }
  recentFailures: Array<{
    executionId: string
    workflowName: string
    errorMessage: string | null
    startedAt: string | null
  }>
}

export function useDashboardMetrics() {
  return useQuery<DashboardMetrics>({
    queryKey: ['dashboard-metrics'],
    queryFn: async () => {
      try {
        const response = await api.get<DashboardMetrics>('/dashboard/metrics')
        console.log('Dashboard metrics response:', response)

        // api.get already returns the parsed JSON, not wrapped in .data
        if (!response) {
          throw new Error('No data returned from dashboard metrics API')
        }

        return response
      } catch (error) {
        console.error('Error fetching dashboard metrics:', error)
        throw error
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 15000, // Consider stale after 15 seconds
    retry: 3, // Retry failed requests 3 times
    retryDelay: 1000, // Wait 1 second between retries
  })
}
