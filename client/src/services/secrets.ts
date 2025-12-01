/**
 * Secrets API service - fully type-safe with openapi-fetch
 *
 * NOTE: These endpoints are not yet implemented in the FastAPI backend.
 * Secrets are currently managed through the /api/config endpoint with type='secret'.
 * This service exists for future implementation and type safety.
 */

import { apiClient } from "@/lib/api-client";

// Define local types since secrets endpoints aren't in OpenAPI spec yet
interface SecretResponse {
	name: string;
	value?: string;
	description?: string | null;
	created_at?: string | null;
	updated_at?: string | null;
}

interface SecretListResponse {
	secrets: string[];
	org_id?: string | null;
	count: number;
}

interface SecretCreateRequest {
	name: string;
	value: string;
	description?: string | null;
}

interface SecretUpdateRequest {
	value: string;
	description?: string | null;
}

/** Helper to extract error message from API error response */
function getErrorMessage(error: unknown, fallback: string): string {
	if (typeof error === "object" && error && "message" in error) {
		return String((error as Record<string, unknown>)["message"]);
	}
	return fallback;
}

/**
 * Helper to check if response is an error (handles both defined and undefined error codes)
 * Returns error message if there's an error, null otherwise
 */
function checkResponseError(
	response: { data?: unknown; error?: unknown; response: Response },
	fallback: string,
): string | null {
	// Check if error field is populated (for defined error responses in OpenAPI spec)
	if (response.error) {
		return getErrorMessage(response.error, fallback);
	}

	// Check HTTP status code directly (handles undefined error codes like 503)
	if (!response.response.ok) {
		// Try to parse error from response body if available
		return fallback;
	}

	// Check if data is missing (shouldn't happen for successful requests)
	if (!response.data) {
		return "An unexpected error occurred";
	}

	return null;
}

export const secretsService = {
	/**
	 * List all secrets
	 * NOTE: Endpoint not yet implemented. Use configService with type='secret' instead.
	 */
	async listSecrets(): Promise<SecretListResponse> {
		const response = await apiClient.GET("/secrets" as never);
		const errorMsg = checkResponseError(response, "Failed to list secrets");
		if (errorMsg) throw new Error(errorMsg);
		return (response.data as unknown) as SecretListResponse;
	},

	/**
	 * Create a new secret
	 * NOTE: Endpoint not yet implemented. Use configService.setConfig with type='secret' instead.
	 */
	async createSecret(request: SecretCreateRequest): Promise<SecretResponse> {
		const response = await apiClient.POST("/secrets" as never, {
			body: request as never,
		} as never);
		const errorMsg = checkResponseError(
			response,
			"Failed to create secret",
		);
		if (errorMsg) throw new Error(errorMsg);
		return (response.data as unknown) as SecretResponse;
	},

	/**
	 * Update an existing secret
	 * NOTE: Endpoint not yet implemented. Use configService.setConfig with type='secret' instead.
	 */
	async updateSecret(
		secretName: string,
		request: SecretUpdateRequest,
	): Promise<SecretResponse> {
		const response = await apiClient.PUT("/secrets/{name}" as never, {
			params: { path: { name: secretName } } as never,
			body: request as never,
		} as never);
		const errorMsg = checkResponseError(
			response,
			"Failed to update secret",
		);
		if (errorMsg) throw new Error(errorMsg);
		return (response.data as unknown) as SecretResponse;
	},

	/**
	 * Delete a secret
	 * NOTE: Endpoint not yet implemented. Use configService.deleteConfig instead.
	 */
	async deleteSecret(secretName: string): Promise<void> {
		const response = await apiClient.DELETE("/secrets/{name}" as never, {
			params: { path: { name: secretName } } as never,
		} as never);
		const errorMsg = checkResponseError(
			response,
			"Failed to delete secret",
		);
		if (errorMsg) throw new Error(errorMsg);
		return (response.data as unknown) as void;
	},
};
