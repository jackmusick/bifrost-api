/**
 * Workflow executions API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
import type { ExecutionFilters } from '@/lib/client-types'

export const executionsService = {
  /**
   * Get all executions with optional filters
   */
  async getExecutions(filters?: ExecutionFilters): Promise<components['schemas']['WorkflowExecution'][]> {
    const params: Record<string, string> = {}

    if (filters?.workflowName) params['workflowName'] = filters.workflowName
    if (filters?.status) params['status'] = filters.status

    const { data, error } = await apiClient.GET('/executions', {
      params: { query: params },
    })

    if (error) throw new Error(`Failed to fetch executions: ${error}`)

    // API returns ExecutionsListResponse with executions array
    if (data && 'executions' in data) {
      return data.executions
    }
    return []
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
