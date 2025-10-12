/**
 * Workflow Keys API Service
 * Manages global and org-specific workflow keys for HTTP-triggered workflows
 */

import { api } from './api'

export interface WorkflowKey {
  scope: 'GLOBAL' | 'org'
  orgId?: string
  key: string  // Masked when retrieved, full when generated
  createdAt: string
  createdBy: string
  lastUsedAt?: string
  message?: string  // Only present when generating
}

export class WorkflowKeysService {
  /**
   * Get workflow key (masked) for a scope
   * @param scope 'global' for GLOBAL keys, 'org' for org-specific
   * @param orgId Organization ID (required for org scope)
   */
  async getWorkflowKey(scope: 'global' | 'org', orgId?: string): Promise<WorkflowKey> {
    const params: Record<string, string> = { scope }
    if (orgId) {
      params['orgId'] = orgId
    }
    return api.get<WorkflowKey>('/workflow-keys', params)
  }

  /**
   * Generate or regenerate a workflow key
   * WARNING: This will replace any existing key for the scope
   * @param scope 'global' for GLOBAL keys, 'org' for org-specific
   * @param orgId Organization ID (required for org scope)
   */
  async generateWorkflowKey(scope: 'global' | 'org', orgId?: string): Promise<WorkflowKey> {
    const params: Record<string, string> = { scope }
    if (orgId) {
      params['orgId'] = orgId
    }
    return api.post<WorkflowKey>('/workflow-keys', undefined, params)
  }

  /**
   * Revoke a workflow key
   * This will prevent all webhook executions for the scope until a new key is generated
   * @param scope 'global' for GLOBAL keys, 'org' for org-specific
   * @param orgId Organization ID (required for org scope)
   */
  async revokeWorkflowKey(scope: 'global' | 'org', orgId?: string): Promise<void> {
    const params: Record<string, string> = { scope }
    if (orgId) {
      params['orgId'] = orgId
    }
    return api.delete('/workflow-keys', params)
  }
}

export const workflowKeysService = new WorkflowKeysService()
