/**
 * Workflows API service
 */

import type { MetadataResponse, WorkflowExecutionRequest, WorkflowExecutionResponse } from '@/types/workflow'

export const workflowsService = {
  /**
   * Get all workflows and data providers metadata
   */
  async getMetadata(): Promise<MetadataResponse> {
    // Call the workflow engine metadata endpoint directly
    const response = await fetch('http://localhost:7072/api/registry/metadata')
    if (!response.ok) {
      throw new Error('Failed to fetch workflows metadata')
    }
    return response.json()
  },

  /**
   * Execute a workflow directly with parameters
   */
  async executeWorkflow(request: WorkflowExecutionRequest): Promise<WorkflowExecutionResponse> {
    // Call workflow engine directly with required headers
    // Body uses flat JSON format (parameters at root level)
    const response = await fetch(`http://localhost:7072/api/workflows/${request.workflowName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Organization-Id': request.orgId || 'org-acme-123',
        'X-User-Id': 'test-user-123', // TODO: Get from auth context
      },
      body: JSON.stringify(request.parameters),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Failed to execute workflow')
    }

    return response.json()
  },
}
