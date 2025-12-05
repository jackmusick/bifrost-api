/**
 * Forms API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";
import type { FormSubmission, FormExecutionResponse } from "@/lib/client-types";

/** Helper to extract error message from API error response */
function getErrorMessage(error: unknown, fallback: string): string {
	if (typeof error === "object" && error && "message" in error) {
		return String((error as Record<string, unknown>)["message"]);
	}
	return fallback;
}

export const formsService = {
	/**
	 * Get all forms
	 */
	async getForms(): Promise<components["schemas"]["FormPublic"][]> {
		const { data, error } = await apiClient.GET("/api/forms");
		if (error)
			throw new Error(getErrorMessage(error, "Failed to fetch forms"));
		return data;
	},

	/**
	 * Get a specific form by ID
	 */
	async getForm(
		formId: string,
	): Promise<components["schemas"]["FormPublic"]> {
		const { data, error } = await apiClient.GET("/api/forms/{form_id}", {
			params: { path: { form_id: formId } },
		});
		if (error)
			throw new Error(getErrorMessage(error, "Failed to fetch form"));
		return data;
	},

	/**
	 * Create a new form
	 */
	async createForm(
		request: components["schemas"]["FormCreate"],
	): Promise<components["schemas"]["FormPublic"]> {
		const { data, error } = await apiClient.POST("/api/forms", {
			body: request,
		});
		if (error)
			throw new Error(getErrorMessage(error, "Failed to create form"));
		return data;
	},

	/**
	 * Update a form
	 */
	async updateForm(
		formId: string,
		request: components["schemas"]["FormUpdate"],
	): Promise<components["schemas"]["FormPublic"]> {
		const { data, error } = await apiClient.PATCH("/api/forms/{form_id}", {
			params: { path: { form_id: formId } },
			body: request,
		});
		if (error)
			throw new Error(getErrorMessage(error, "Failed to update form"));
		return data;
	},

	/**
	 * Delete a form (soft delete - sets isActive=false)
	 */
	async deleteForm(formId: string): Promise<void> {
		const { error } = await apiClient.DELETE("/api/forms/{form_id}", {
			params: { path: { form_id: formId } },
		});
		if (error)
			throw new Error(getErrorMessage(error, "Failed to delete form"));
	},

	/**
	 * Execute a form to run workflow
	 */
	async submitForm(
		submission: FormSubmission,
	): Promise<FormExecutionResponse> {
		const { data, error } = await apiClient.POST(
			"/api/forms/{form_id}/execute",
			{
				params: { path: { form_id: submission.form_id } },
				body: { form_data: submission.form_data },
			},
		);
		if (error || !data) {
			throw new Error(getErrorMessage(error, "Failed to submit form"));
		}
		return data as FormExecutionResponse;
	},
};
