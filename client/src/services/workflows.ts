/**
 * Workflows API service
 * Uses centralized api client which automatically handles X-Organization-Id
 */

import { api } from './api'
import type { MetadataResponse, WorkflowExecutionRequest, WorkflowExecutionResponse } from '@/types/workflow'

export const workflowsService = {
  /**
   * Get all workflows and data providers metadata
   * Organization context is handled automatically by the api client
   */
  async getMetadata(): Promise<MetadataResponse> {
    return api.get<MetadataResponse>('/workflows/metadata')
  },

  /**
   * Execute a workflow with parameters
   * Organization context is handled automatically by the api client
   *
   * @param request - Workflow execution request
   * @param request.orgId - Optional: only provide if admin overriding context
   * @param request.userId - Optional: only provide if admin overriding context
   */
  async executeWorkflow(request: WorkflowExecutionRequest): Promise<WorkflowExecutionResponse> {
    // Use api.request to allow optional orgId/userId override for admin use case
    return api.request<WorkflowExecutionResponse>(`/workflows/${request.workflowName}`, {
      method: 'POST',
      body: JSON.stringify(request.parameters),
      orgId: request.orgId,
      userId: request.userId
    })
  },
}
