/**
 * Data Providers API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Auto-generated types from OpenAPI spec
export type DataProvider = components["schemas"]["DataProviderMetadata"];

// TODO: These types will be added when the data provider options endpoint is implemented
export type DataProviderOption = {
	label: string;
	value: string;
	description?: string;
};
export type DataProviderResponse = { options: DataProviderOption[] };

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
	 * NOTE: This endpoint is currently not implemented in the API.
	 * The getOptions method is a placeholder for when it becomes available.
	 *
	 * @param _formId - Form ID (UUID)
	 * @param _providerName - Data provider name
	 * @param _inputs - Optional input parameters for the data provider
	 */
	async getOptions(
		formId: string,
		providerName: string,
		inputs?: Record<string, unknown>,
	): Promise<DataProviderOption[]> {
		// TODO: Implement when endpoint /api/forms/{form_id}/data-providers/{provider_name} is available
		// For now, return empty options
		void formId;
		void providerName;
		void inputs;
		return [];
	},
};
