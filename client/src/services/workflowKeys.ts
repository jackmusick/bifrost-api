/**
 * Workflow Keys API service - fully type-safe with openapi-fetch
 * Uses auto-generated types from OpenAPI spec
 *
 * NOTE: Workflow keys may be moving to workflows table - review this service
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Auto-generated types from OpenAPI spec
export type WorkflowKeyCreateRequest =
	components["schemas"]["WorkflowKeyCreateRequest"];
export type WorkflowKeyResponse = components["schemas"]["WorkflowKeyResponse"];

export const workflowKeysService = {
	/**
	 * List all workflow API keys for the current user
	 */
	async listWorkflowKeys(params?: {
		workflowId?: string;
		includeRevoked?: boolean;
	}): Promise<WorkflowKeyResponse[]> {
		// Build query string manually since params aren't in OpenAPI spec
		const queryParams = new URLSearchParams();
		if (params?.workflowId)
			queryParams.set("workflow_id", params.workflowId);
		if (params?.includeRevoked !== undefined)
			queryParams.set("include_revoked", String(params.includeRevoked));

		const queryString = queryParams.toString();
		const url = queryString
			? `/api/workflow-keys?${queryString}`
			: "/api/workflow-keys";

		const { data, error } = await apiClient.GET(
			url as "/api/workflow-keys",
		);

		if (error) {
			throw new Error(`Failed to list workflow keys: ${error}`);
		}

		return (data as WorkflowKeyResponse[]) || [];
	},

	/**
	 * Create a new workflow API key
	 */
	async createWorkflowKey(
		request: WorkflowKeyCreateRequest,
	): Promise<WorkflowKeyResponse> {
		const { data, error } = await apiClient.POST("/api/workflow-keys", {
			body: request as never,
		});

		if (error) {
			throw new Error(`Failed to create workflow key: ${error}`);
		}

		return data as WorkflowKeyResponse;
	},

	/**
	 * Revoke a workflow API key
	 */
	async revokeWorkflowKey(workflowId: string): Promise<void> {
		const { error } = await apiClient.DELETE(
			"/api/workflow-keys/{workflow_id}",
			{
				params: { path: { workflow_id: workflowId } },
			},
		);

		if (error) {
			throw new Error(`Failed to revoke workflow key: ${error}`);
		}
	},
};
