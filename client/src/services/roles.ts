/**
 * Roles API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Type aliases for cleaner code
type RolePublic = components["schemas"]["RolePublic"];
type RoleCreate = components["schemas"]["RoleCreate"];
type RoleUpdate = components["schemas"]["RoleUpdate"];
type AssignUsersToRoleRequest =
	components["schemas"]["AssignUsersToRoleRequest"];
type AssignFormsToRoleRequest =
	components["schemas"]["AssignFormsToRoleRequest"];

/** Helper to extract error message from API error response */
function getErrorMessage(error: unknown, fallback: string): string {
	if (typeof error === "object" && error && "message" in error) {
		return (error as { message: string }).message;
	}
	return fallback;
}

export const rolesService = {
	/**
	 * Get all roles
	 */
	async getRoles(): Promise<RolePublic[]> {
		const { data, error } = await apiClient.GET("/api/roles");
		if (error) throw new Error(`Failed to fetch roles: ${error}`);
		return data || [];
	},

	/**
	 * Create a new role
	 */
	async createRole(request: RoleCreate): Promise<RolePublic> {
		const { data, error } = await apiClient.POST("/api/roles", {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			body: request as any, // OpenAPI spec incorrectly expects full Role instead of RoleCreate
		});
		if (error) throw new Error(`Failed to create role: ${error}`);
		return data!;
	},

	/**
	 * Update a role
	 */
	async updateRole(roleId: string, request: RoleUpdate): Promise<RolePublic> {
		const { data, error } = await apiClient.PATCH("/api/roles/{role_id}", {
			params: { path: { role_id: roleId } },
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			body: request as any, // OpenAPI spec incorrectly expects full Role instead of RoleUpdate
		});
		if (error) throw new Error(`Failed to update role: ${error}`);
		return data!;
	},

	/**
	 * Delete a role (soft delete)
	 */
	async deleteRole(roleId: string): Promise<void> {
		const { data, error } = await apiClient.DELETE("/api/roles/{role_id}", {
			params: { path: { role_id: roleId } },
		});
		if (error) throw new Error(`Failed to delete role: ${error}`);
		return data;
	},

	/**
	 * Get users in a role
	 */
	async getRoleUsers(roleId: string) {
		const { data, error } = await apiClient.GET(
			"/api/roles/{role_id}/users",
			{
				params: { path: { role_id: roleId } },
			},
		);
		if (error) throw new Error(`Failed to fetch role users: ${error}`);
		return data;
	},

	/**
	 * Assign users to a role (batch)
	 */
	async assignUsersToRole(
		roleId: string,
		request: AssignUsersToRoleRequest,
	): Promise<void> {
		const { error } = await apiClient.POST("/api/roles/{role_id}/users", {
			params: { path: { role_id: roleId } },
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			body: request as any, // OpenAPI spec type mismatch
		});
		if (error) throw new Error(`Failed to assign users to role: ${error}`);
	},

	/**
	 * Remove a user from a role
	 */
	async removeUserFromRole(roleId: string, userId: string): Promise<void> {
		const { data, error } = await apiClient.DELETE(
			"/api/roles/{role_id}/users/{user_id}",
			{
				params: { path: { role_id: roleId, user_id: userId } },
			},
		);
		if (error) throw new Error(`Failed to remove user from role: ${error}`);
		return data;
	},

	/**
	 * Get forms assigned to a role
	 */
	async getRoleForms(roleId: string) {
		const { data, error } = await apiClient.GET(
			"/api/roles/{role_id}/forms",
			{
				params: { path: { role_id: roleId } },
			},
		);
		if (error) throw new Error(`Failed to fetch role forms: ${error}`);
		return data;
	},

	/**
	 * Assign forms to a role (batch)
	 */
	async assignFormsToRole(
		roleId: string,
		request: AssignFormsToRoleRequest,
	): Promise<void> {
		const { error } = await apiClient.POST("/api/roles/{role_id}/forms", {
			params: { path: { role_id: roleId } },
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			body: request as any, // OpenAPI spec type mismatch
		});
		if (error)
			throw new Error(
				getErrorMessage(error, "Failed to assign forms to role"),
			);
	},

	/**
	 * Assign roles to a form (helper that calls assignFormsToRole for each role)
	 * This handles the form->roles relationship properly
	 */
	async assignRolesToForm(formId: string, roleIds: string[]): Promise<void> {
		// TODO: Implement once form->roles endpoints are available
		// For now, assign each role to this form
		for (const roleId of roleIds) {
			await this.assignFormsToRole(roleId, { formIds: [formId] });
		}
	},
};
