/**
 * OAuth Connections API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";
import type { OAuthAuthorizeResponse } from "@/lib/client-types";

// Type aliases for cleaner code
type OAuthConnectionDetail = components["schemas"]["OAuthConnectionDetail"];
type OAuthConnectionListResponse =
	components["schemas"]["OAuthConnectionListResponse"];
type CreateOAuthConnectionRequest =
	components["schemas"]["CreateOAuthConnectionRequest"];
type UpdateOAuthConnectionRequest =
	components["schemas"]["UpdateOAuthConnectionRequest"];

/**
 * Extract meaningful error message from API error object
 */
function formatError(error: unknown): string {
	if (typeof error === "string") return error;
	if (typeof error === "object" && error !== null) {
		const err = error as { message?: string; error?: string };
		return err.message || err.error || JSON.stringify(error);
	}
	return String(error);
}

export const oauthService = {
	/**
	 * List all OAuth connections
	 */
	async listConnections(): Promise<OAuthConnectionListResponse> {
		const { data, error } = await apiClient.GET("/api/oauth/connections");
		if (error)
			throw new Error(
				`Failed to list OAuth connections: ${formatError(error)}`,
			);
		return data!;
	},

	/**
	 * Get OAuth connection details by name
	 */
	async getConnection(
		connectionName: string,
	): Promise<OAuthConnectionDetail> {
		const { data, error } = await apiClient.GET(
			"/api/oauth/connections/{connection_name}",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to get OAuth connection: ${formatError(error)}`,
			);
		return data!;
	},

	/**
	 * Create a new OAuth connection
	 */
	async createConnection(
		request: CreateOAuthConnectionRequest,
	): Promise<OAuthConnectionDetail> {
		const { data, error } = await apiClient.POST("/api/oauth/connections", {
			body: request,
		});
		if (error)
			throw new Error(
				`Failed to create OAuth connection: ${formatError(error)}`,
			);
		return data!;
	},

	/**
	 * Update an existing OAuth connection
	 */
	async updateConnection(
		connectionName: string,
		request: UpdateOAuthConnectionRequest,
	): Promise<OAuthConnectionDetail> {
		const { data, error } = await apiClient.PUT(
			"/api/oauth/connections/{connection_name}",
			{
				params: { path: { connection_name: connectionName } },
				body: request,
			},
		);
		if (error)
			throw new Error(
				`Failed to update OAuth connection: ${formatError(error)}`,
			);
		return data!;
	},

	/**
	 * Delete an OAuth connection
	 */
	async deleteConnection(connectionName: string): Promise<void> {
		const { data, error } = await apiClient.DELETE(
			"/api/oauth/connections/{connection_name}",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to delete OAuth connection: ${formatError(error)}`,
			);
		return data;
	},

	/**
	 * Initiate OAuth authorization flow
	 * Returns authorization URL for user to visit
	 */
	async authorize(connectionName: string): Promise<OAuthAuthorizeResponse> {
		const { data, error } = await apiClient.POST(
			"/api/oauth/connections/{connection_name}/authorize",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to authorize OAuth connection: ${formatError(error)}`,
			);
		return data as OAuthAuthorizeResponse;
	},

	/**
	 * Cancel OAuth authorization (reset to not_connected status)
	 */
	async cancelAuthorization(connectionName: string) {
		const { data, error } = await apiClient.POST(
			"/api/oauth/connections/{connection_name}/cancel",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to cancel OAuth authorization: ${formatError(error)}`,
			);
		return data;
	},

	/**
	 * Manually refresh OAuth access token using refresh token
	 */
	async refreshToken(
		connectionName: string,
	): Promise<{ success: boolean; message: string; expires_at: string }> {
		const { data, error } = await apiClient.POST(
			"/api/oauth/connections/{connection_name}/refresh",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to refresh OAuth token: ${formatError(error)}`,
			);
		return data as unknown as {
			success: boolean;
			message: string;
			expires_at: string;
		};
	},

	/**
	 * Handle OAuth callback (exchange authorization code for tokens)
	 * Called from the UI callback page after OAuth provider redirects
	 */
	async handleCallback(
		connectionName: string,
		code: string,
		state?: string | null,
	) {
		const { data, error } = await apiClient.POST(
			"/api/oauth/callback/{connection_name}",
			{
				params: { path: { connection_name: connectionName } },
				body: {
					code,
					state: state ?? null,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
				} as any, // Type mismatch in OpenAPI spec
			},
		);
		if (error)
			throw new Error(
				`Failed to handle OAuth callback: ${formatError(error)}`,
			);
		return data;
	},

	/**
	 * Get OAuth credentials for workflow consumption
	 * WARNING: Returns sensitive access tokens
	 */
	async getCredentials(connectionName: string) {
		const { data, error } = await apiClient.GET(
			"/api/oauth/credentials/{connection_name}",
			{
				params: { path: { connection_name: connectionName } },
			},
		);
		if (error)
			throw new Error(
				`Failed to get OAuth credentials: ${formatError(error)}`,
			);
		return data;
	},

	/**
	 * Test OAuth connection by checking status
	 */
	async testConnection(
		connectionName: string,
	): Promise<{ success: boolean; message: string }> {
		const connection = await this.getConnection(connectionName);
		if (!connection) {
			return {
				success: false,
				message: "Connection not found",
			};
		}
		return {
			success: connection.status === "completed",
			message:
				connection.status_message ||
				`Connection status: ${connection.status}`,
		};
	},

	/**
	 * Get OAuth refresh job status
	 */
	async getRefreshJobStatus() {
		const { data, error } = await apiClient.GET(
			"/api/oauth/refresh_job_status",
		);
		if (error)
			throw new Error(
				`Failed to get refresh job status: ${formatError(error)}`,
			);
		return data;
	},

	/**
	 * Manually trigger the OAuth token refresh job
	 */
	async triggerRefreshJob() {
		const { data, error } = await apiClient.POST("/api/oauth/refresh_all");
		if (error)
			throw new Error(
				`Failed to trigger refresh job: ${formatError(error)}`,
			);
		return data;
	},
};
