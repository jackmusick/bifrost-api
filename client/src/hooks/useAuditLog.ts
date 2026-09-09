import { $api } from "@/lib/api-client";
import { sameQueryParamsExcept } from "@/lib/paginated-query";
import type { components } from "@/lib/v1";

export type AuditLogEntry = components["schemas"]["AuditLogEntry"];
export type AuditLogListResponse =
	components["schemas"]["AuditLogListResponse"];

export interface GetAuditLogParams {
	action?: string;
	resource_type?: string;
	outcome?: string;
	user_id?: string;
	start_date?: string;
	end_date?: string;
	search?: string;
	limit?: number;
	continuation_token?: string;
}

export function useAuditLog(
	params: GetAuditLogParams = {},
	enabled = true,
	options: { preservePageData?: boolean } = {},
) {
	return $api.useQuery(
		"get",
		"/api/audit",
		{
			params: {
				query: params as Record<string, string | number | undefined>,
			},
		},
		{
			enabled,
			placeholderData: options.preservePageData
				? (previousData, previousQuery) =>
						sameQueryParamsExcept({ ...params }, previousQuery, [
							"continuation_token",
						])
							? previousData
							: undefined
				: undefined,
		},
	);
}
