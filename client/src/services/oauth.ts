/**
 * OAuth Connections API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
import type { OAuthAuthorizeResponse } from '@/lib/client-types'

export const oauthService = {
  /**
   * List all OAuth connections
   */
  async listConnections() {
    const { data, error } = await apiClient.GET('/oauth/connections')
    if (error) throw new Error(`Failed to list OAuth connections: ${error}`)
    return data
  },

  /**
   * Get OAuth connection details by name
   */
  async getConnection(connectionName: string) {
    const { data, error } = await apiClient.GET('/oauth/connections/{connection_name}', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to get OAuth connection: ${error}`)
    return data
  },

  /**
   * Create a new OAuth connection
   */
  async createConnection(request: components['schemas']['CreateOAuthConnectionRequest']) {
    const { data, error } = await apiClient.POST('/oauth/connections', {
      body: request,
    })
    if (error) throw new Error(`Failed to create OAuth connection: ${error}`)
    return data
  },

  /**
   * Update an existing OAuth connection
   */
  async updateConnection(
    connectionName: string,
    request: components['schemas']['UpdateOAuthConnectionRequest']
  ) {
    const { data, error } = await apiClient.PUT('/oauth/connections/{connection_name}', {
      params: { path: { connection_name: connectionName } },
      body: request,
    })
    if (error) throw new Error(`Failed to update OAuth connection: ${error}`)
    return data
  },

  /**
   * Delete an OAuth connection
   */
  async deleteConnection(connectionName: string) {
    const { data, error } = await apiClient.DELETE('/oauth/connections/{connection_name}', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to delete OAuth connection: ${error}`)
    return data
  },

  /**
   * Initiate OAuth authorization flow
   * Returns authorization URL for user to visit
   */
  async authorize(connectionName: string): Promise<OAuthAuthorizeResponse> {
    const { data, error } = await apiClient.POST('/oauth/connections/{connection_name}/authorize', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to authorize OAuth connection: ${error}`)
    // @ts-expect-error - Response type extends API type with authorization_url
    return data as OAuthAuthorizeResponse
  },

  /**
   * Cancel OAuth authorization (reset to not_connected status)
   */
  async cancelAuthorization(connectionName: string) {
    const { data, error } = await apiClient.POST('/oauth/connections/{connection_name}/cancel', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to cancel OAuth authorization: ${error}`)
    return data
  },

  /**
   * Manually refresh OAuth access token using refresh token
   */
  async refreshToken(connectionName: string): Promise<{ success: boolean; message: string; expires_at: string }> {
    const { data, error } = await apiClient.POST('/oauth/connections/{connection_name}/refresh', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to refresh OAuth token: ${error}`)
    return data as { success: boolean; message: string; expires_at: string }
  },

  /**
   * Handle OAuth callback (exchange authorization code for tokens)
   * Called from the UI callback page after OAuth provider redirects
   */
  async handleCallback(connectionName: string, code: string, state?: string | null) {
    const { data, error } = await apiClient.POST('/oauth/callback/{connection_name}', {
      params: { path: { connection_name: connectionName } },
      body: { code, state: state || undefined },
    })
    if (error) throw new Error(`Failed to handle OAuth callback: ${error}`)
    return data
  },

  /**
   * Get OAuth credentials for workflow consumption
   * WARNING: Returns sensitive access tokens
   */
  async getCredentials(connectionName: string) {
    const { data, error } = await apiClient.GET('/oauth/credentials/{connection_name}', {
      params: { path: { connection_name: connectionName } },
    })
    if (error) throw new Error(`Failed to get OAuth credentials: ${error}`)
    return data
  },

  /**
   * Test OAuth connection by checking status
   */
  async testConnection(connectionName: string): Promise<{ success: boolean; message: string }> {
    const connection = await this.getConnection(connectionName)
    return {
      success: connection.status === 'completed',
      message: connection.status_message || 'Connection status: ' + connection.status,
    }
  },
}
