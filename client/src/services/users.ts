/**
 * Users API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components, paths } from "@/lib/v1";

// Type aliases for cleaner code
type UserPublic = components["schemas"]["UserPublic"];
type UserCreate =
	paths["/api/users"]["post"]["requestBody"]["content"]["application/json"];
type UserUpdate =
	paths["/api/users/{user_id}"]["patch"]["requestBody"]["content"]["application/json"];

export const usersService = {
	/**
	 * Get all users filtered by current scope (from X-Organization-Id header)
	 */
	async getUsers(): Promise<UserPublic[]> {
		const { data, error } = await apiClient.GET("/api/users");
		if (error) throw new Error(`Failed to fetch users: ${error}`);
		return data || [];
	},

	/**
	 * Get a specific user by ID
	 */
	async getUser(userId: string): Promise<UserPublic> {
		const { data, error } = await apiClient.GET("/api/users/{user_id}", {
			params: { path: { user_id: userId } },
		});
		if (error) throw new Error(`Failed to fetch user: ${error}`);
		return data!;
	},

	// User permissions system has been deprecated and removed

	/**
	 * Get roles for a user
	 */
	async getUserRoles(userId: string) {
		const { data, error } = await apiClient.GET(
			"/api/users/{user_id}/roles",
			{
				params: { path: { user_id: userId } },
			},
		);
		if (error) throw new Error(`Failed to fetch user roles: ${error}`);
		return data;
	},

	/**
	 * Get user forms
	 */
	async getUserForms(userId: string) {
		const { data, error } = await apiClient.GET(
			"/api/users/{user_id}/forms",
			{
				params: { path: { user_id: userId } },
			},
		);
		if (error) throw new Error(`Failed to fetch user forms: ${error}`);
		return data;
	},

	/**
	 * Create a new user
	 */
	async createUser(body: UserCreate): Promise<UserPublic> {
		const { data, error } = await apiClient.POST("/api/users", {
			body,
		});
		if (error) throw new Error(`Failed to create user: ${error}`);
		return data!;
	},

	/**
	 * Update a user
	 */
	async updateUser(userId: string, body: UserUpdate): Promise<UserPublic> {
		const { data, error } = await apiClient.PATCH("/api/users/{user_id}", {
			params: { path: { user_id: userId } },
			body,
		});
		if (error) throw new Error(`Failed to update user: ${error}`);
		return data!;
	},

	/**
	 * Delete a user
	 */
	async deleteUser(userId: string): Promise<void> {
		const { error } = await apiClient.DELETE("/api/users/{user_id}", {
			params: { path: { user_id: userId } },
		});
		if (error) throw new Error(`Failed to delete user: ${error}`);
	},
};
