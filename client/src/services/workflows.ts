/**
 * Workflows API service - fully type-safe with openapi-fetch
 */

import { apiClient, withContext } from "@/lib/api-client";
import type { components, paths } from "@/lib/v1";

// Type aliases for cleaner code using paths for response types
type WorkflowExecutionRequest = components["schemas"]["WorkflowExecutionRequest"];
type WorkflowExecutionResponse = paths["/api/workflows/execute"]["post"]["responses"]["200"]["content"]["application/json"];
type WorkflowValidationRequest = components["schemas"]["WorkflowValidationRequest"];
type WorkflowValidationResponse = components["schemas"]["WorkflowValidationResponse"];
type WorkflowsListResponse = paths["/api/workflows"]["get"]["responses"]["200"]["content"]["application/json"];

export const workflowsService = {
	/**
	 * Get all workflows metadata
	 */
	async getWorkflows(): Promise<WorkflowsListResponse> {
		const { data, error } = await apiClient.GET("/api/workflows", {});
		if (error) throw new Error(`Failed to fetch workflows: ${error}`);
		return data!;
	},

	/**
	 * Execute a workflow with parameters or inline code
	 * @param workflowName - Name of the workflow to execute (optional for scripts)
	 * @param parameters - Workflow input parameters
	 * @param transient - Optional: skip database persistence (for editor debugging)
	 * @param code - Optional: base64-encoded Python code to execute as script
	 * @param scriptName - Optional: script identifier for logging (when code is provided)
	 * @param options - Optional: override organization context (admin only)
	 */
	async executeWorkflow(
		workflowName: string | undefined,
		parameters: Record<string, unknown>,
		transient?: boolean,
		code?: string,
		scriptName?: string,
		options?: { orgId?: string; userId?: string },
	): Promise<WorkflowExecutionResponse> {
		const client =
			options?.orgId && options?.userId
				? withContext(options.orgId, options.userId)
				: apiClient;

		// Note: After regenerating types with npm run generate:types, this will be properly typed
		const { data, error } = await client.POST("/api/workflows/execute", {
			body: {
				workflow_name: workflowName ?? null,
				input_data: parameters,
				form_id: null,
				transient: transient ?? false,
				code: code ?? null,
				scriptName: scriptName ?? null,
			} as WorkflowExecutionRequest,
		});

		if (error) throw new Error(`Failed to execute workflow: ${error}`);
		return data!;
	},

	/**
	 * Validate a workflow file for syntax errors and decorator issues
	 * @param path - Relative workspace path to the workflow file
	 * @param content - Optional file content to validate (if not provided, reads from disk)
	 */
	async validateWorkflow(
		path: string,
		content?: string,
	): Promise<WorkflowValidationResponse> {
		const { data, error } = await apiClient.POST("/api/workflows/validate", {
			body: {
				path,
				content: content ?? null,
			} as WorkflowValidationRequest,
		});

		if (error) throw new Error(`Failed to validate workflow: ${error}`);
		return data!;
	},
};
