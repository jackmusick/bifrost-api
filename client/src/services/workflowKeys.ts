/**
 * Workflow Keys API service - fully type-safe with openapi-fetch
 */

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
		// Temporary: Use fetch directly since apiClient types are incomplete
		const orgId = localStorage.getItem("selectedOrgId");
		const url = new URL("/api/workflow-keys", window.location.origin);
		if (params?.workflowId) {
			url.searchParams.set("workflowId", params.workflowId);
		}
		if (params?.includeRevoked !== undefined) {
			url.searchParams.set(
				"includeRevoked",
				params.includeRevoked.toString(),
			);
		}

		const response = await fetch(url.toString(), {
			headers: {
				"X-Organization-Id": orgId || "",
			},
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to list workflow keys: ${error}`);
		}

		return response.json();
	},

	/**
	 * Create a new workflow API key
	 */
	async createWorkflowKey(
		request: WorkflowKeyCreateRequest,
	): Promise<WorkflowKeyResponse> {
		const orgId = localStorage.getItem("selectedOrgId");
		const response = await fetch("/api/workflow-keys", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Organization-Id": orgId || "",
			},
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to create workflow key: ${error}`);
		}

		return response.json();
	},

	/**
	 * Revoke a workflow API key
	 */
	async revokeWorkflowKey(keyId: string): Promise<void> {
		const orgId = localStorage.getItem("selectedOrgId");
		const response = await fetch(`/api/workflow-keys/${keyId}`, {
			method: "DELETE",
			headers: {
				"X-Organization-Id": orgId || "",
			},
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to revoke workflow key: ${error}`);
		}
	},
};
