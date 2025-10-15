/**
 * Workflow executions API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
import type { ExecutionFilters, ExecutionListResponse } from '@/lib/client-types'

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

    // OpenAPI spec says single object, but API likely returns array or wrapped object
    // Handle both cases for robustness
    if (Array.isArray(data)) {
      return data as components['schemas']['WorkflowExecution'][]
    }
    // @ts-expect-error - API may return {executions: [...]} despite spec saying otherwise
    if (data && typeof data === 'object' && 'executions' in data) {
      // @ts-expect-error - See above
      return data.executions || []
    }
    // If it's a single execution object, wrap in array
    return data ? [data as components['schemas']['WorkflowExecution']] : []
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
