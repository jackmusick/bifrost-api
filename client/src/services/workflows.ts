/**
 * Workflows API service
 */

import type { MetadataResponse, WorkflowExecutionRequest, WorkflowExecutionResponse } from '@/types/workflow'

export const workflowsService = {
  /**
   * Get all workflows and data providers metadata
   */
  async getMetadata(): Promise<MetadataResponse> {
    // Call Management API which proxies to workflows engine
    // Management API handles authentication and workflows engine configuration
    const response = await fetch('/api/workflows/metadata', {
      credentials: 'same-origin', // Include cookies for SWA auth
    })
    if (!response.ok) {
      throw new Error('Failed to fetch workflows metadata')
    }
    return response.json()
  },

  /**
   * Execute a workflow with parameters
   * Auth is handled automatically by SWA via X-MS-CLIENT-PRINCIPAL header
   * Organization and user context are derived from auth by Management API
   *
   * @param request - Workflow execution request
   * @param request.orgId - Optional: only provide if admin overriding context
   * @param request.userId - Optional: only provide if admin overriding context
   */
  async executeWorkflow(request: WorkflowExecutionRequest): Promise<WorkflowExecutionResponse> {
    // Call via SWA proxy (not direct to Azure Functions)
    // Management API derives X-Organization-Id and X-User-Id from auth by default
    // Only PlatformAdmins can override these headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // Only add override headers if explicitly provided (admin use case)
    if (request.orgId) {
      headers['X-Organization-Id'] = request.orgId
    }
    if (request.userId) {
      headers['X-User-Id'] = request.userId
    }

    const response = await fetch(`/api/workflows/${request.workflowName}`, {
      method: 'POST',
      headers,
      credentials: 'same-origin', // Include cookies for SWA auth
      body: JSON.stringify(request.parameters),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Failed to execute workflow')
    }

    return response.json()
  },
}
