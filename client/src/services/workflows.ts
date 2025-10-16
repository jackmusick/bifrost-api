/**
 * Workflows API service - fully type-safe with openapi-fetch
 */

import { apiClient, withContext } from '@/lib/api-client'
import type { components } from '@/lib/v1'

export const workflowsService = {
  /**
   * Get all workflows and data providers metadata
   */
  async getMetadata() {
    const { data, error } = await apiClient.GET('/discovery')
    if (error) throw new Error(`Failed to fetch metadata: ${error}`)
    return data
  },

  /**
   * Execute a workflow with parameters
   * @param workflowName - Name of the workflow to execute
   * @param parameters - Workflow input parameters
   * @param orgId - Optional: override organization context (admin only)
   * @param userId - Optional: override user context (admin only)
   */
  async executeWorkflow(
    workflowName: string,
    parameters: Record<string, unknown>,
    options?: { orgId?: string; userId?: string }
  ) {
    const client = options?.orgId && options?.userId
      ? withContext(options.orgId, options.userId)
      : apiClient

    const { data, error } = await client.POST('/workflows/{workflowName}/execute', {
      params: { path: { workflowName } },
      body: {
        inputData: parameters,
      } as components['schemas']['WorkflowExecutionRequest'],
    })

    if (error) throw new Error(`Failed to execute workflow: ${error}`)
    return data
  },
}
