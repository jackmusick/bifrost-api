/**
 * Config API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

export const configService = {
    /**
     * Get all configs (global or org-specific)
     */
    async getConfigs(params?: { scope?: "global" | "org" }) {
        const { data, error } = await apiClient.GET("/config", {
            params: { query: params as Record<string, string> },
        });
        if (error) throw new Error(`Failed to fetch configs: ${error}`);
        return data;
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
    async deleteConfig(key: string, params?: { scope?: "global" | "org" }) {
        const { data, error } = await apiClient.DELETE("/config/{key}", {
            params: {
                path: { key },
                query: params as Record<string, string>,
            },
        });
        if (error) throw new Error(`Failed to delete config: ${error}`);
        return data;
    },
};
