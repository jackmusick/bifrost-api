/**
 * React Query hook for execution logs (admin only)
 * Uses openapi-react-query for type-safe API access
 */

import { $api } from "@/lib/api-client";
import { sameQueryParamsExcept } from "@/lib/paginated-query";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type LogListEntry = components["schemas"]["LogListEntry"];
export type LogsListResponse = components["schemas"]["LogsListResponse"];

export interface LogFilters {
	workflow_id?: string;
	global_only?: boolean;
	organization_id?: string;
	workflow_name?: string;
	levels?: string; // Comma-separated: "ERROR,WARNING"
	message_search?: string;
	start_date?: string;
	end_date?: string;
	limit?: number;
}

/**
 * Hook to fetch execution logs with filtering and pagination (admin only)
 * @param filters - Log filter criteria
 * @param continuationToken - Pagination token for next page
 * @param enabled - Whether the query should run
 */
export function useLogs(
	filters?: LogFilters,
	continuationToken?: string,
	enabled: boolean = true,
	options: { preservePageData?: boolean } = {},
) {
	const queryParams: Record<string, string | number | boolean> = {};
	if (filters?.global_only) queryParams.global_only = true;
	if (filters?.workflow_id) queryParams.workflow_id = filters.workflow_id;

	if (filters?.organization_id) {
		queryParams["organization_id"] = filters.organization_id;
	}
	if (filters?.workflow_name) {
		queryParams["workflow_name"] = filters.workflow_name;
	}
	if (filters?.levels) {
		queryParams["levels"] = filters.levels;
	}
	if (filters?.message_search) {
		queryParams["message_search"] = filters.message_search;
	}
	if (filters?.start_date) {
		queryParams["start_date"] = filters.start_date;
	}
	if (filters?.end_date) {
		queryParams["end_date"] = filters.end_date;
	}
	if (filters?.limit) {
		queryParams["limit"] = filters.limit;
	}
	if (continuationToken) {
		queryParams["continuation_token"] = continuationToken;
	}

	return $api.useQuery(
		"get",
		"/api/executions/logs",
		{ params: { query: queryParams } },
		{
			enabled,
			placeholderData: options.preservePageData
				? (previousData, previousQuery) =>
						sameQueryParamsExcept(queryParams, previousQuery, [
							"continuation_token",
						])
							? previousData
							: undefined
				: undefined,
		},
	);
}
