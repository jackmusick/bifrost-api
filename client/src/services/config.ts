/**
 * Config API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Type aliases for cleaner code
type Config = components["schemas"]["Config"];
type SetConfigRequest = components["schemas"]["SetConfigRequest"];

/** Helper to extract error message from API error response */
function getErrorMessage(error: unknown): string {
	if (typeof error === "object" && error && "message" in error) {
		return String((error as Record<string, unknown>)["message"]);
	}
	return JSON.stringify(error);
}

export const configService = {
	/**
	 * Get all configs for current scope
	 * Scope is determined by X-Organization-Id header (set automatically by apiClient)
	 */
	async getConfigs(): Promise<Config[]> {
		// Scope is determined by X-Organization-Id header
		const { data, error } = await apiClient.GET("/api/config");
		if (error) {
			const message = getErrorMessage(error);
			throw new Error(`Failed to fetch configs: ${message}`);
		}
		return data || [];
	},

	/**
	 * Set a config value
	 */
	async setConfig(request: SetConfigRequest): Promise<Config> {
		const { data, error } = await apiClient.POST("/api/config", {
			body: request,
		});
		if (error) {
			const message = getErrorMessage(error);
			throw new Error(message);
		}
		return data!;
	},

	/**
	 * Delete a config
	 */
	async deleteConfig(key: string): Promise<void> {
		const { data, error } = await apiClient.DELETE("/api/config/{key}", {
			params: {
				path: { key },
			},
		});
		if (error) {
			const message = getErrorMessage(error);
			throw new Error(message);
		}
		return data;
	},
};
