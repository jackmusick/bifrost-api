import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

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
        const { data, error } = await apiClient.GET('/metrics')
        if (error) throw new Error(`Failed to fetch dashboard metrics: ${error}`)
        return data as DashboardMetrics
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
