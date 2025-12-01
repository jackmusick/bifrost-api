/**
 * Organizations API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Type aliases for cleaner code
type OrganizationPublic = components["schemas"]["OrganizationPublic"];
type OrganizationCreate = components["schemas"]["OrganizationCreate"];
type OrganizationUpdate = components["schemas"]["OrganizationUpdate"];

export const organizationsService = {
	/**
	 * Get all organizations
	 */
	async getOrganizations(): Promise<OrganizationPublic[]> {
		const { data, error } = await apiClient.GET("/api/organizations");
		if (error) throw new Error(`Failed to fetch organizations: ${error}`);
		return data || [];
	},

	/**
	 * Get a specific organization by ID
	 */
	async getOrganization(orgId: string): Promise<OrganizationPublic> {
		const { data, error } = await apiClient.GET("/api/organizations/{org_id}", {
			params: { path: { org_id: orgId } },
		});
		if (error) throw new Error(`Failed to fetch organization: ${error}`);
		return data!;
	},

	/**
	 * Create a new organization
	 */
	async createOrganization(
		request: OrganizationCreate,
	): Promise<OrganizationPublic> {
		const { data, error } = await apiClient.POST("/api/organizations", {
			body: request,
		});
		if (error) throw new Error(`Failed to create organization: ${error}`);
		return data!;
	},

	/**
	 * Update an existing organization
	 */
	async updateOrganization(
		orgId: string,
		request: OrganizationUpdate,
	): Promise<OrganizationPublic> {
		const { data, error } = await apiClient.PATCH(
			"/api/organizations/{org_id}",
			{
				params: { path: { org_id: orgId } },
				body: request,
			},
		);
		if (error) throw new Error(`Failed to update organization: ${error}`);
		return data!;
	},

	/**
	 * Delete an organization
	 */
	async deleteOrganization(orgId: string): Promise<void> {
		const { data, error } = await apiClient.DELETE(
			"/api/organizations/{org_id}",
			{
				params: { path: { org_id: orgId } },
			},
		);
		if (error) throw new Error(`Failed to delete organization: ${error}`);
		return data;
	},
};
