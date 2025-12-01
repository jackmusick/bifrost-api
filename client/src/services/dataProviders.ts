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
		const { data, error } = await apiClient.GET("/api/data-providers", {});
		if (error) throw new Error(`Failed to fetch data providers: ${error}`);
		return data;
	},

	/**
	 * Get options from a data provider in the context of a form
	 *
	 * This endpoint enforces form access control - user must have access
	 * to view the form before they can call data providers.
	 *
	 * @param formId - Form ID (UUID)
	 * @param providerName - Data provider name
	 * @param inputs - Optional input parameters for the data provider
	 */
	async getOptions(
		formId: string,
		providerName: string,
		inputs?: Record<string, unknown>,
	): Promise<DataProviderOption[]> {
		const { data, error } = await apiClient.POST(
			"/api/forms/{form_id}/data-providers/{provider_name}",
			{
				params: { path: { form_id: formId, provider_name: providerName } },
				body: inputs
					? { org_id: null, inputs, no_cache: false }
					: { org_id: null, inputs: null, no_cache: false },
			},
		);
		if (error)
			throw new Error(`Failed to fetch data provider options: ${error}`);
		return (data as DataProviderResponse)?.options || [];
	},
};
