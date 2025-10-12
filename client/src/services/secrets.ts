/**
 * Secrets API service
 */

import { api } from './api'
import type {
  SecretListResponse,
  SecretCreateRequest,
  SecretUpdateRequest,
  SecretResponse,
  KeyVaultHealthResponse,
} from '@/types/secret'

export const secretsService = {
  /**
   * List all secrets, optionally filtered by organization
   */
  async listSecrets(orgId?: string): Promise<SecretListResponse> {
    const params = orgId ? { org_id: orgId } : undefined
    return api.get<SecretListResponse>('/secrets', params)
  },

  /**
   * Create a new secret
   */
  async createSecret(data: SecretCreateRequest): Promise<SecretResponse> {
    return api.post<SecretResponse>('/secrets', data)
  },

  /**
   * Update an existing secret
   */
  async updateSecret(secretName: string, data: SecretUpdateRequest): Promise<SecretResponse> {
    return api.put<SecretResponse>(`/secrets/${secretName}`, data)
  },

  /**
   * Delete a secret
   */
  async deleteSecret(secretName: string): Promise<SecretResponse> {
    return api.delete<SecretResponse>(`/secrets/${secretName}`)
  },

  /**
   * Check Key Vault health status
   */
  async getHealthStatus(): Promise<KeyVaultHealthResponse> {
    return api.get<KeyVaultHealthResponse>('/health/keyvault')
  },
}
