/**
 * Roles API service
 */

import { api } from './api'
import type {
  Role,
  CreateRoleRequest,
  UpdateRoleRequest,
  UserRole,
  FormRole,
  AssignUsersToRoleRequest,
  AssignFormsToRoleRequest,
} from '@/types/role'

export const rolesService = {
  /**
   * Get all roles
   */
  async getRoles(): Promise<Role[]> {
    return api.get<Role[]>('/roles')
  },

  /**
   * Create a new role
   */
  async createRole(request: CreateRoleRequest): Promise<Role> {
    return api.post<Role>('/roles', request)
  },

  /**
   * Update a role
   */
  async updateRole(roleId: string, request: UpdateRoleRequest): Promise<Role> {
    return api.put<Role>(`/roles/${roleId}`, request)
  },

  /**
   * Delete a role (soft delete)
   */
  async deleteRole(roleId: string): Promise<void> {
    return api.delete<void>(`/roles/${roleId}`)
  },

  /**
   * Get users in a role
   */
  async getRoleUsers(roleId: string): Promise<UserRole[]> {
    return api.get<UserRole[]>(`/roles/${roleId}/users`)
  },

  /**
   * Assign users to a role (batch)
   */
  async assignUsersToRole(roleId: string, request: AssignUsersToRoleRequest): Promise<void> {
    return api.post<void>(`/roles/${roleId}/users`, request)
  },

  /**
   * Remove a user from a role
   */
  async removeUserFromRole(roleId: string, userId: string): Promise<void> {
    return api.delete<void>(`/roles/${roleId}/users/${userId}`)
  },

  /**
   * Get forms assigned to a role
   */
  async getRoleForms(roleId: string): Promise<FormRole[]> {
    return api.get<FormRole[]>(`/roles/${roleId}/forms`)
  },

  /**
   * Assign forms to a role (batch)
   */
  async assignFormsToRole(roleId: string, request: AssignFormsToRoleRequest): Promise<void> {
    return api.post<void>(`/roles/${roleId}/forms`, request)
  },

  /**
   * Remove a form from a role
   */
  async removeFormFromRole(roleId: string, formId: string): Promise<void> {
    return api.delete<void>(`/roles/${roleId}/forms/${formId}`)
  },
}
