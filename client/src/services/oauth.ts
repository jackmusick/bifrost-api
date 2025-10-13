/**
 * OAuth Connections API service
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
   * List all OAuth connections for an organization
   * Always includes GLOBAL connections as fallback
   */
  async listConnections(
    orgId?: string
  ): Promise<OAuthConnectionSummary[]> {
    return api.request<OAuthConnectionSummary[]>('/oauth/connections', {
      method: 'GET',
      orgId,
    })
  },

  /**
   * Get OAuth connection details by name
   */
  async getConnection(
    connectionName: string,
    orgId?: string
  ): Promise<OAuthConnectionDetail> {
    return api.request<OAuthConnectionDetail>(`/oauth/connections/${connectionName}`, {
      method: 'GET',
      orgId,
    })
  },

  /**
   * Create a new OAuth connection
   */
  async createConnection(
    data: CreateOAuthConnectionRequest,
    orgId?: string
  ): Promise<OAuthConnectionDetail> {
    return api.request<OAuthConnectionDetail>('/oauth/connections', {
      method: 'POST',
      body: JSON.stringify(data),
      orgId,
    })
  },

  /**
   * Update an existing OAuth connection
   */
  async updateConnection(
    connectionName: string,
    data: UpdateOAuthConnectionRequest,
    orgId?: string
  ): Promise<OAuthConnectionDetail> {
    return api.request<OAuthConnectionDetail>(`/oauth/connections/${connectionName}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      orgId,
    })
  },

  /**
   * Delete an OAuth connection
   */
  async deleteConnection(
    connectionName: string,
    orgId?: string
  ): Promise<void> {
    return api.request<void>(`/oauth/connections/${connectionName}`, {
      method: 'DELETE',
      orgId,
    })
  },

  /**
   * Initiate OAuth authorization flow
   * Returns authorization URL for user to visit
   */
  async authorize(
    connectionName: string,
    orgId?: string
  ): Promise<OAuthAuthorizeResponse> {
    return api.request<OAuthAuthorizeResponse>(
      `/oauth/connections/${connectionName}/authorize`,
      {
        method: 'POST',
        body: JSON.stringify({}),
        orgId,
      }
    )
  },

  /**
   * Cancel OAuth authorization (reset to not_connected status)
   */
  async cancelAuthorization(
    connectionName: string,
    orgId?: string
  ): Promise<void> {
    return api.request<void>(
      `/oauth/connections/${connectionName}/cancel`,
      {
        method: 'POST',
        body: JSON.stringify({}),
        orgId,
      }
    )
  },

  /**
   * Manually refresh OAuth access token using refresh token
   */
  async refreshToken(
    connectionName: string,
    orgId?: string
  ): Promise<{ success: boolean; message: string; expires_at: string }> {
    return api.request<{ success: boolean; message: string; expires_at: string }>(
      `/oauth/connections/${connectionName}/refresh`,
      {
        method: 'POST',
        body: JSON.stringify({}),
        orgId,
      }
    )
  },

  /**
   * Handle OAuth callback (exchange authorization code for tokens)
   * Called from the UI callback page after OAuth provider redirects
   */
  async handleCallback(
    connectionName: string,
    code: string,
    state?: string | null
  ): Promise<void> {
    return api.request<void>(
      `/oauth/callback/${connectionName}`,
      {
        method: 'POST',
        body: JSON.stringify({ code, state }),
      }
    )
  },

  /**
   * Get OAuth credentials for workflow consumption
   * WARNING: Returns sensitive access tokens
   */
  async getCredentials(
    connectionName: string,
    orgId?: string
  ): Promise<OAuthCredentialsResponse> {
    return api.request<OAuthCredentialsResponse>(`/oauth/credentials/${connectionName}`, {
      method: 'GET',
      orgId,
    })
  },

  /**
   * Test OAuth connection by making a test API call
   * This is called automatically after OAuth flow completes
   */
  async testConnection(
    connectionName: string,
    orgId?: string
  ): Promise<{ success: boolean; message: string }> {
    // Not a direct API endpoint - this happens automatically in the callback
    // But we can check status by fetching connection details
    const connection = await this.getConnection(connectionName, orgId)
    return {
      success: connection.status === 'completed',
      message: connection.status_message || 'Connection status: ' + connection.status
    }
  }
}
