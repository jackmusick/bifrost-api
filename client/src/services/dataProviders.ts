/**
 * Data Providers API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type DataProviderOption = components["schemas"]["DataProviderOption"];
export type DataProviderResponse =
    components["schemas"]["DataProviderResponse"];

export const dataProvidersService = {
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
