/**
 * OAuth Connections API service
 * All methods use the centralized api client which automatically handles
 * X-Organization-Id header from sessionStorage.
 * Optional orgId parameter allows admin override when needed.
 */

import { api } from './api'
import type {
  OAuthConnectionSummary,
  OAuthConnectionDetail,
  CreateOAuthConnectionRequest,
  UpdateOAuthConnectionRequest,
  OAuthAuthorizeResponse,
  OAuthCredentialsResponse,
} from '@/types/oauth'

export const oauthService = {
  /**
   * List all OAuth connections
   * Organization context is handled automatically by the api client
   * Always includes GLOBAL connections as fallback
   */
  async listConnections(): Promise<OAuthConnectionSummary[]> {
    return api.get<OAuthConnectionSummary[]>('/oauth/connections')
  },

  /**
   * Get OAuth connection details by name
   * Organization context is handled automatically by the api client
   */
  async getConnection(connectionName: string): Promise<OAuthConnectionDetail> {
    return api.get<OAuthConnectionDetail>(`/oauth/connections/${connectionName}`)
  },

  /**
   * Create a new OAuth connection
   * Organization context is handled automatically by the api client
   */
  async createConnection(data: CreateOAuthConnectionRequest): Promise<OAuthConnectionDetail> {
    return api.post<OAuthConnectionDetail>('/oauth/connections', data)
  },

  /**
   * Update an existing OAuth connection
   * Organization context is handled automatically by the api client
   */
  async updateConnection(
    connectionName: string,
    data: UpdateOAuthConnectionRequest
  ): Promise<OAuthConnectionDetail> {
    return api.put<OAuthConnectionDetail>(`/oauth/connections/${connectionName}`, data)
  },

  /**
   * Delete an OAuth connection
   * Organization context is handled automatically by the api client
   */
  async deleteConnection(connectionName: string): Promise<void> {
    return api.delete<void>(`/oauth/connections/${connectionName}`)
  },

  /**
   * Initiate OAuth authorization flow
   * Returns authorization URL for user to visit
   * Organization context is handled automatically by the api client
   */
  async authorize(connectionName: string): Promise<OAuthAuthorizeResponse> {
    return api.post<OAuthAuthorizeResponse>(`/oauth/connections/${connectionName}/authorize`, {})
  },

  /**
   * Cancel OAuth authorization (reset to not_connected status)
   * Organization context is handled automatically by the api client
   */
  async cancelAuthorization(connectionName: string): Promise<void> {
    return api.post<void>(`/oauth/connections/${connectionName}/cancel`, {})
  },

  /**
   * Manually refresh OAuth access token using refresh token
   * Organization context is handled automatically by the api client
   */
  async refreshToken(
    connectionName: string
  ): Promise<{ success: boolean; message: string; expires_at: string }> {
    return api.post<{ success: boolean; message: string; expires_at: string }>(
      `/oauth/connections/${connectionName}/refresh`,
      {}
    )
  },

  /**
   * Handle OAuth callback (exchange authorization code for tokens)
   * Called from the UI callback page after OAuth provider redirects
   * Organization context is handled automatically by the api client
   */
  async handleCallback(
    connectionName: string,
    code: string,
    state?: string | null
  ): Promise<void> {
    return api.post<void>(`/oauth/callback/${connectionName}`, { code, state })
  },

  /**
   * Get OAuth credentials for workflow consumption
   * WARNING: Returns sensitive access tokens
   * Organization context is handled automatically by the api client
   */
  async getCredentials(connectionName: string): Promise<OAuthCredentialsResponse> {
    return api.get<OAuthCredentialsResponse>(`/oauth/credentials/${connectionName}`)
  },

  /**
   * Test OAuth connection by making a test API call
   * This is called automatically after OAuth flow completes
   */
  async testConnection(
    connectionName: string
  ): Promise<{ success: boolean; message: string }> {
    // Not a direct API endpoint - this happens automatically in the callback
    // But we can check status by fetching connection details
    const connection = await this.getConnection(connectionName)
    return {
      success: connection.status === 'completed',
      message: connection.status_message || 'Connection status: ' + connection.status
    }
  }
}
