/**
 * Workflow executions API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components, paths } from "@/lib/v1";
import type { ExecutionFilters } from "@/lib/client-types";

// Type aliases for cleaner code
type WorkflowExecution = components["schemas"]["WorkflowExecution"];
type ExecutionListResponse =
	paths["/api/executions"]["get"]["responses"]["200"]["content"]["application/json"];

export const executionsService = {
	/**
	 * Get all executions with optional filters and pagination
	 */
	async getExecutions(
		filters?: ExecutionFilters,
		continuationToken?: string,
	): Promise<ExecutionListResponse> {
		const params: Record<string, string> = {};

		if (filters?.workflow_name)
			params["workflow_name"] = filters.workflow_name;
		if (filters?.status) params["status"] = filters.status;
		if (filters?.start_date) params["start_date"] = filters.start_date;
		if (filters?.end_date) params["end_date"] = filters.end_date;
		if (filters?.limit) params["limit"] = filters.limit.toString();
		if (continuationToken) params["continuation_token"] = continuationToken;

		const { data, error } = await apiClient.GET("/api/executions", {
			params: { query: params },
		});

		if (error) throw new Error(`Failed to fetch executions: ${error}`);

		return data!;
	},

	/**
	 * Get a specific execution by ID
	 */
	async getExecution(executionId: string): Promise<WorkflowExecution> {
		const { data, error } = await apiClient.GET(
			"/api/executions/{execution_id}",
			{
				params: { path: { execution_id: executionId } },
			},
		);
		if (error) throw new Error(`Failed to fetch execution: ${error}`);
		return data!;
	},

	/**
	 * Get only the result of an execution (progressive loading)
	 */
	async getExecutionResult(executionId: string) {
		const { data, error } = await apiClient.GET(
			"/api/executions/{execution_id}/result",
			{
				params: { path: { execution_id: executionId } },
			},
		);
		if (error)
			throw new Error(`Failed to fetch execution result: ${error}`);
		return data;
	},

	/**
	 * Get only the logs of an execution (progressive loading, admin only)
	 * Returns array of log entries
	 */
	async getExecutionLogs(
		executionId: string,
	): Promise<Record<string, unknown>[]> {
		const { data, error } = await apiClient.GET(
			"/api/executions/{execution_id}/logs",
			{
				params: { path: { execution_id: executionId } },
			},
		);
		if (error) throw new Error(`Failed to fetch execution logs: ${error}`);
		return data as Record<string, unknown>[];
	},

	/**
	 * Get only the variables of an execution (progressive loading, admin only)
	 * Returns variables object
	 */
	async getExecutionVariables(
		executionId: string,
	): Promise<Record<string, unknown>> {
		const { data, error } = await apiClient.GET(
			"/api/executions/{execution_id}/variables",
			{
				params: { path: { execution_id: executionId } },
			},
		);
		if (error)
			throw new Error(`Failed to fetch execution variables: ${error}`);
		return data as Record<string, unknown>;
	},

	/**
	 * Cancel a pending or running execution
	 */
	async cancelExecution(executionId: string) {
		const { data, error } = await apiClient.POST(
			"/api/executions/{execution_id}/cancel",
			{
				params: { path: { execution_id: executionId } },
			},
		);
		if (error) throw new Error(`Failed to cancel execution: ${error}`);
		return data;
	},
};
