/**
 * Workflow Keys API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";

// Inline types until v1.d.ts is regenerated from API
export interface WorkflowKeyCreateRequest {
	workflow_id?: string | undefined;
	expires_in_days?: number | undefined;
	description?: string | undefined;
}

export interface WorkflowKeyResponse {
	id: string;
	workflow_id?: string | null;
	masked_key: string;
	raw_key?: string | null; // Only present on creation
	description?: string | null;
	created_at?: string | null;
	created_by?: string | null;
	expires_at?: string | null;
	revoked_at?: string | null;
	last_used_at?: string | null;
}

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
		if (params?.workflowId) queryParams.set("workflow_id", params.workflowId);
		if (params?.includeRevoked !== undefined)
			queryParams.set("include_revoked", String(params.includeRevoked));

		const queryString = queryParams.toString();
		const url = queryString
			? `/api/workflow-keys?${queryString}`
			: "/api/workflow-keys";

		const { data, error } = await apiClient.GET(url as "/api/workflow-keys");

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
	async revokeWorkflowKey(keyId: string): Promise<void> {
		const { error } = await apiClient.DELETE("/api/workflow-keys/{key_id}", {
			params: { path: { key_id: keyId } },
		});

		if (error) {
			throw new Error(`Failed to revoke workflow key: ${error}`);
		}
	},
};
