/**
 * Users API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { paths } from '@/lib/v1'

export const usersService = {
  /**
   * Get all users with optional type filtering
   */
  async getUsers(params?: paths['/users']['get']['parameters']['query']) {
    const { data, error } = await apiClient.GET('/users', {
      ...(params && { params: { query: params } }),
    })
    if (error) throw new Error(`Failed to fetch users: ${error}`)
    return data || []
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

  // User permissions system has been deprecated and removed

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
