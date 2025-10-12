/**
 * Organizations API service
 */

import { api } from './api'
import type { Organization, CreateOrganizationRequest, UpdateOrganizationRequest } from '@/types/organization'

export const organizationsService = {
  /**
   * Get all organizations
   */
  async getOrganizations(): Promise<Organization[]> {
    return api.get<Organization[]>('/organizations')
  },

  /**
   * Get a specific organization by ID
   */
  async getOrganization(orgId: string): Promise<Organization> {
    return api.get<Organization>(`/organizations/${orgId}`)
  },

  /**
   * Create a new organization
   */
  async createOrganization(data: CreateOrganizationRequest): Promise<Organization> {
    return api.post<Organization>('/organizations', data)
  },

  /**
   * Update an existing organization
   */
  async updateOrganization(orgId: string, data: UpdateOrganizationRequest): Promise<Organization> {
    return api.put<Organization>(`/organizations/${orgId}`, data)
  },

  /**
   * Delete an organization
   */
  async deleteOrganization(orgId: string): Promise<void> {
    return api.delete<void>(`/organizations/${orgId}`)
  },
}
