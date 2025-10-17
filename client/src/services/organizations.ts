/**
 * Organizations API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'

export const organizationsService = {
  /**
   * Get all organizations
   */
  async getOrganizations() {
    const { data, error } = await apiClient.GET('/organizations')
    if (error) throw new Error(`Failed to fetch organizations: ${error}`)
    return data || []
  },

  /**
   * Get a specific organization by ID
   */
  async getOrganization(orgId: string) {
    const { data, error } = await apiClient.GET('/organizations/{orgId}', {
      params: { path: { orgId } },
    })
    if (error) throw new Error(`Failed to fetch organization: ${error}`)
    return data
  },

  /**
   * Create a new organization
   */
  async createOrganization(request: components['schemas']['CreateOrganizationRequest']) {
    const { data, error } = await apiClient.POST('/organizations', {
      body: request,
    })
    if (error) throw new Error(`Failed to create organization: ${error}`)
    return data
  },

  /**
   * Update an existing organization
   */
  async updateOrganization(orgId: string, request: components['schemas']['UpdateOrganizationRequest']) {
    const { data, error } = await apiClient.PATCH('/organizations/{orgId}', {
      params: { path: { orgId } },
      body: request,
    })
    if (error) throw new Error(`Failed to update organization: ${error}`)
    return data
  },

  /**
   * Delete an organization
   */
  async deleteOrganization(orgId: string) {
    const { data, error } = await apiClient.DELETE('/organizations/{orgId}', {
      params: { path: { orgId } },
    })
    if (error) throw new Error(`Failed to delete organization: ${error}`)
    return data
  },
}
