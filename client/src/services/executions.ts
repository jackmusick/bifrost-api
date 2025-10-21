/**
 * Workflow executions API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
import type { ExecutionFilters } from '@/lib/client-types'

export const executionsService = {
  /**
   * Get all executions with optional filters and pagination
   */
  async getExecutions(
    filters?: ExecutionFilters,
    continuationToken?: string
  ): Promise<{ executions: components['schemas']['WorkflowExecution'][]; continuationToken: string | null; hasMore: boolean }> {
    const params: Record<string, string> = {}

    if (filters?.workflowName) params['workflowName'] = filters.workflowName
    if (filters?.status) params['status'] = filters.status
    if (filters?.limit) params['limit'] = filters.limit.toString()
    if (continuationToken) params['continuationToken'] = continuationToken

    const { data, error } = await apiClient.GET('/executions', {
      params: { query: params },
    })

    if (error) throw new Error(`Failed to fetch executions: ${error}`)

    // API now returns paginated response
    return data as any || { executions: [], continuationToken: null, hasMore: false }
  },

  /**
   * Get a specific execution by ID
   */
  async getExecution(executionId: string) {
    const { data, error } = await apiClient.GET('/executions/{executionId}', {
      params: { path: { executionId } },
    })
    if (error) throw new Error(`Failed to fetch execution: ${error}`)
    return data
  },
}
