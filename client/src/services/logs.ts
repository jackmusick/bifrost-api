import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type SystemLog = components["schemas"]["SystemLog"];
export type SystemLogsListResponse =
	components["schemas"]["SystemLogsListResponse"];

export interface GetSystemLogsParams {
	category?: string;
	level?: string;
	startDate?: string;
	endDate?: string;
	limit?: number;
	continuationToken?: string;
}

/** Helper to extract error message from API error response */
function getErrorMessage(error: unknown, fallback: string): string {
	if (typeof error === "object" && error && "error" in error) {
		return String((error as Record<string, unknown>)["error"]);
	}
	return fallback;
}

export async function getSystemLogs(
	params: GetSystemLogsParams = {},
): Promise<SystemLogsListResponse> {
	const { data, error } = await apiClient.GET("/api/logs", {
		params: {
			query: params as Record<string, string | number>,
		},
	});

	if (error) {
		throw new Error(getErrorMessage(error, "Failed to fetch system logs"));
	}

	return data!;
}

export async function getSystemLog(
	category: string,
	rowKey: string,
): Promise<SystemLog> {
	const { data, error } = await apiClient.GET(
		"/api/logs/{category}/{row_key}",
		{
			params: {
				path: { category, row_key: rowKey },
			},
		},
	);

	if (error) {
		throw new Error(getErrorMessage(error, "Failed to fetch system log"));
	}

	return data!;
}
