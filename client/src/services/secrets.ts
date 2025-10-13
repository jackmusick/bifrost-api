/**
 * Secrets API service
 * All methods use the centralized api client which automatically handles
 * X-Organization-Id header from sessionStorage
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
   * List all secrets
   * Organization context is handled automatically by the api client
   */
  async listSecrets(): Promise<SecretListResponse> {
    return api.get<SecretListResponse>('/secrets')
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
