/**
 * Workflow executions API service
 */

import { api } from './api'
import type { WorkflowExecution, ExecutionFilters, ExecutionListResponse } from '@/types/execution'

export const executionsService = {
  /**
   * Get all executions with optional filters
   */
  async getExecutions(filters?: ExecutionFilters): Promise<WorkflowExecution[]> {
    const params: Record<string, string> = {}

    if (filters?.orgId) params['orgId'] = filters.orgId
    if (filters?.workflowName) params['workflowName'] = filters.workflowName
    if (filters?.status) params['status'] = filters.status
    if (filters?.limit) params['limit'] = filters.limit.toString()
    if (filters?.continuationToken) params['continuationToken'] = filters.continuationToken

    const response = await api.get<ExecutionListResponse>('/executions', params)

    // Return just the executions array for backwards compatibility
    return response.executions
  },

  /**
   * Get a specific execution by ID
   */
  async getExecution(executionId: string, orgId: string): Promise<WorkflowExecution> {
    return api.get<WorkflowExecution>(`/executions/${executionId}`, { orgId })
  },
}
