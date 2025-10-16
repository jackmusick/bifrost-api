/**
 * Secrets API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'

export const secretsService = {
  /**
   * List all secrets
   */
  async listSecrets() {
    const { data, error } = await apiClient.GET('/secrets')
    if (error) throw new Error(`Failed to list secrets: ${error}`)
    return data
  },

  /**
   * Create a new secret
   */
  async createSecret(request: components['schemas']['SecretCreateRequest']) {
    const { data, error } = await apiClient.POST('/secrets', {
      body: request,
    })
    if (error) throw new Error(`Failed to create secret: ${error}`)
    return data
  },

  /**
   * Update an existing secret
   */
  async updateSecret(secretName: string, request: components['schemas']['SecretUpdateRequest']) {
    const { data, error } = await apiClient.PUT('/secrets/{name}', {
      params: { path: { name: secretName } },
      body: request,
    })
    if (error) throw new Error(`Failed to update secret: ${error}`)
    return data
  },

  /**
   * Delete a secret
   */
  async deleteSecret(secretName: string) {
    const { data, error } = await apiClient.DELETE('/secrets/{name}', {
      params: { path: { name: secretName } },
    })
    if (error) throw new Error(`Failed to delete secret: ${error}`)
    return data
  },
}
