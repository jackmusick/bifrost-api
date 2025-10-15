/**
 * Roles API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'

export const rolesService = {
  /**
   * Get all roles
   */
  async getRoles() {
    const { data, error } = await apiClient.GET('/roles')
    if (error) throw new Error(`Failed to fetch roles: ${error}`)
    return data
  },

  /**
   * Create a new role
   */
  async createRole(request: components['schemas']['CreateRoleRequest']) {
    const { data, error } = await apiClient.POST('/roles', {
      body: request,
    })
    if (error) throw new Error(`Failed to create role: ${error}`)
    return data
  },

  /**
   * Update a role
   */
  async updateRole(roleId: string, request: components['schemas']['UpdateRoleRequest']) {
    const { data, error } = await apiClient.PUT('/roles/{roleId}', {
      params: { path: { roleId } },
      body: request,
    })
    if (error) throw new Error(`Failed to update role: ${error}`)
    return data
  },

  /**
   * Delete a role (soft delete)
   */
  async deleteRole(roleId: string) {
    const { data, error } = await apiClient.DELETE('/roles/{roleId}', {
      params: { path: { roleId } },
    })
    if (error) throw new Error(`Failed to delete role: ${error}`)
    return data
  },

  /**
   * Get users in a role
   */
  async getRoleUsers(roleId: string) {
    const { data, error } = await apiClient.GET('/roles/{roleId}/users', {
      params: { path: { roleId } },
    })
    if (error) throw new Error(`Failed to fetch role users: ${error}`)
    return data
  },

  /**
   * Assign users to a role (batch)
   */
  async assignUsersToRole(roleId: string, request: components['schemas']['AssignUsersToRoleRequest']) {
    const { data, error } = await apiClient.POST('/roles/{roleId}/users', {
      params: { path: { roleId } },
      body: request,
    })
    if (error) throw new Error(`Failed to assign users to role: ${error}`)
    return data
  },

  /**
   * Remove a user from a role
   */
  async removeUserFromRole(roleId: string, userId: string) {
    const { data, error } = await apiClient.DELETE('/roles/{roleId}/users/{userId}', {
      params: { path: { roleId, userId } },
    })
    if (error) throw new Error(`Failed to remove user from role: ${error}`)
    return data
  },

  /**
   * Get forms assigned to a role
   */
  async getRoleForms(roleId: string) {
    const { data, error } = await apiClient.GET('/roles/{roleId}/forms', {
      params: { path: { roleId } },
    })
    if (error) throw new Error(`Failed to fetch role forms: ${error}`)
    return data
  },

  /**
   * Assign forms to a role (batch)
   */
  async assignFormsToRole(roleId: string, request: components['schemas']['AssignFormsToRoleRequest']) {
    const { data, error } = await apiClient.POST('/roles/{roleId}/forms', {
      params: { path: { roleId } },
      body: request,
    })
    if (error) throw new Error(`Failed to assign forms to role: ${error}`)
    return data
  },

  /**
   * Remove a form from a role
   */
  async removeFormFromRole(roleId: string, formId: string) {
    const { data, error } = await apiClient.DELETE('/roles/{roleId}/forms/{formId}', {
      params: { path: { roleId, formId } },
    })
    if (error) throw new Error(`Failed to remove form from role: ${error}`)
    return data
  },
}
