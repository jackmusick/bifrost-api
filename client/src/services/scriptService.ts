/**
 * Script Execution API service
 */

export interface ScriptExecutionRequest {
	code: string;
	timeout_seconds?: number;
}

export interface ScriptExecutionResponse {
	executionId: string;
	status: "Success" | "Failed";
	output: string;
	result?: Record<string, string>;
	error?: string;
	durationMs: number;
	startedAt: string;
	completedAt: string;
}

export const scriptService = {
	/**
	 * Execute a Python script
	 */
	async execute(
		request: ScriptExecutionRequest,
	): Promise<ScriptExecutionResponse> {
		const response = await fetch("/api/scripts/execute", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ message: response.statusText }));
			throw new Error(
				error.message ||
					`Failed to execute script: ${response.statusText}`,
			);
		}

		return response.json();
	},
};
