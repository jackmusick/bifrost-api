/**
 * Data Providers API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type DataProviderOption = components["schemas"]["DataProviderOption"];
export type DataProviderResponse =
    components["schemas"]["DataProviderResponse"];

export type DataProvider = components["schemas"]["DataProviderMetadata"];

export const dataProvidersService = {
    /**
     * Get all data providers
     */
    async getAllProviders() {
        const { data, error } = await apiClient.GET("/data-providers");
        if (error)
            throw new Error(`Failed to fetch data providers: ${error}`);
        return data;
    },
    
    /**
     * Get options from a data provider
     */
    async getOptions(providerName: string): Promise<DataProviderOption[]> {
        const { data, error } = await apiClient.GET(
            "/data-providers/{providerName}",
            {
                params: { path: { providerName } },
            }
        );
        if (error)
            throw new Error(`Failed to fetch data provider options: ${error}`);
        return data.options;
    },
};
