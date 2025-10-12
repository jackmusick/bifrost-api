/**
 * Users API service
 */

import { api } from './api'
import type { User, UserPermission, GrantPermissionsRequest } from '@/types/user'
import type { UserRole } from '@/types/role'

export const usersService = {
  /**
   * Get all users with optional type filtering
   */
  async getUsers(params?: { type?: 'msp' | 'org'; orgId?: string }): Promise<User[]> {
    return api.get<User[]>('/users', params as Record<string, string>)
  },

  /**
   * Get a specific user by ID
   */
  async getUser(userId: string): Promise<User> {
    return api.get<User>(`/users/${userId}`)
  },

  /**
   * Get user permissions for an organization
   */
  async getUserPermissions(userId: string, orgId: string): Promise<UserPermission> {
    return api.get<UserPermission>(`/users/${userId}/permissions`, { orgId })
  },

  /**
   * Get all permissions for an organization
   */
  async getOrgPermissions(orgId: string): Promise<UserPermission[]> {
    return api.get<UserPermission[]>('/permissions', { orgId })
  },

  /**
   * Grant permissions to a user
   */
  async grantPermissions(request: GrantPermissionsRequest): Promise<UserPermission> {
    return api.post<UserPermission>('/permissions', request)
  },

  /**
   * Revoke permissions from a user
   */
  async revokePermissions(userId: string, orgId: string): Promise<void> {
    return api.delete<void>(`/permissions/${userId}/${orgId}`)
  },

  /**
   * Get user's roles
   */
  async getUserRoles(userId: string): Promise<UserRole[]> {
    return api.get<UserRole[]>(`/users/${userId}/roles`)
  },

  /**
   * Get forms a user can access
   */
  async getUserForms(userId: string): Promise<{
    userType: string
    hasAccessToAllForms: boolean
    formIds: string[]
  }> {
    return api.get(`/users/${userId}/forms`)
  },
}
