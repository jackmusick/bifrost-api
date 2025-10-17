/**
 * Config API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

export const configService = {
    /**
     * Get all configs for current scope
     * Scope is determined by X-Organization-Id header (set automatically by apiClient)
     */
    async getConfigs() {
        // Scope is determined by X-Organization-Id header
        const { data, error } = await apiClient.GET("/config");
        if (error) throw new Error(`Failed to fetch configs: ${error}`);
        return data || [];
    },

    /**
     * Set a config value
     */
    async setConfig(request: components["schemas"]["SetConfigRequest"]) {
        const { data, error } = await apiClient.POST("/config", {
            body: request,
        });
        if (error) throw new Error(`Failed to set config: ${error}`);
        return data;
    },

    /**
     * Delete a config
     */
    async deleteConfig(key: string) {
        const { data, error } = await apiClient.DELETE("/config/{key}", {
            params: {
                path: { key },
            },
        });
        if (error) throw new Error(`Failed to delete config: ${error}`);
        return data;
    },
};
