/**
 * Users API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'

export const usersService = {
  /**
   * Get all users with optional type filtering
   */
  async getUsers(params?: { type?: string; orgId?: string }) {
    const { data, error } = await apiClient.GET('/users', {
      params: { query: params as Record<string, string> },
    })
    if (error) throw new Error(`Failed to fetch users: ${error}`)
    return data
  },

  /**
   * Get a specific user by ID
   */
  async getUser(userId: string) {
    const { data, error } = await apiClient.GET('/users/{userId}', {
      params: { path: { userId } },
    })
    if (error) throw new Error(`Failed to fetch user: ${error}`)
    return data
  },

  /**
   * Get user permissions for an organization
   * DEPRECATED: Returns empty list - use role-based access control instead
   */
  async getUserPermissions(userId: string) {
    const { data, error } = await apiClient.GET('/permissions/users/{userId}', {
      params: { path: { userId } },
    })
    if (error) throw new Error(`Failed to fetch user permissions: ${error}`)
    return data
  },

  /**
   * Get all permissions for an organization
   * DEPRECATED: Returns empty list - use role-based access control instead
   */
  async getOrgPermissions(orgId: string) {
    const { data, error } = await apiClient.GET('/permissions/organizations/{orgId}', {
      params: { path: { orgId } },
    })
    if (error) throw new Error(`Failed to fetch org permissions: ${error}`)
    return data
  },

  /**
   * Grant permissions to a user
   */
  async grantPermissions(request: components['schemas']['GrantPermissionsRequest']) {
    const { data, error } = await apiClient.POST('/permissions', {
      body: request,
    })
    if (error) throw new Error(`Failed to grant permissions: ${error}`)
    return data
  },

  /**
   * Revoke permissions from a user
   * DEPRECATED: Returns 501 Not Implemented - use role-based access control instead
   */
  async revokePermissions(userId: string, orgId: string) {
    const { data, error } = await apiClient.DELETE('/permissions', {
      params: { query: { userId, orgId } },
    })
    if (error) throw new Error(`Failed to revoke permissions: ${error}`)
    return data
  },

  /**
   * Get roles for a user
   */
  async getUserRoles(userId: string) {
    const { data, error } = await apiClient.GET('/users/{userId}/roles', {
      params: { path: { userId } },
    })
    if (error) throw new Error(`Failed to fetch user roles: ${error}`)
    return data
  },

  /**
   * Get user forms
   */
  async getUserForms(userId: string) {
    const { data, error } = await apiClient.GET('/users/{userId}/forms', {
      params: { path: { userId } },
    })
    if (error) throw new Error(`Failed to fetch user forms: ${error}`)
    return data
  },
}
