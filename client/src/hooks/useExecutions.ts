/**
 * React Query hooks for workflow executions
 */

import { useQuery } from "@tanstack/react-query";
import { executionsService } from "@/services/executions";
import type { ExecutionFilters } from "@/lib/client-types";
import { useScopeStore } from "@/stores/scopeStore";

export function useExecutions(
	filters?: ExecutionFilters,
	continuationToken?: string,
) {
	const orgId = useScopeStore((state) => state.scope.orgId);

	return useQuery({
		queryKey: ["executions", orgId, filters, continuationToken],
		queryFn: async () => {
			// orgId is sent via X-Organization-Id header (handled by api.ts from sessionStorage)
			// We include orgId in the key so React Query automatically refetches when scope changes
			const response = await executionsService.getExecutions(
				filters,
				continuationToken,
			);
			// Return full response with pagination support
			return response;
		},
		staleTime: 0, // No caching - always fetch fresh data
		refetchOnMount: true,
		refetchOnWindowFocus: false,
	});
}

export function useExecution(
	executionId: string | undefined,
	disablePolling = false,
) {
	return useQuery({
		queryKey: ["executions", executionId],
		queryFn: () => executionsService.getExecution(executionId!),
		enabled: !!executionId,
		staleTime: 0, // No caching - always fetch fresh data
		refetchInterval: (query) => {
			// Disable polling if Web PubSub is handling updates
			if (disablePolling) {
				return false;
			}

			// Poll every 2 seconds if status is Pending or Running
			// This gives a near-real-time experience in local dev without Web PubSub
			// In production with Web PubSub, this is just a backup
			const status = query.state.data?.status;
			return status === "Pending" || status === "Running" ? 2000 : false;
		},
	});
}

/**
 * Progressive loading hook: Get only execution result
 */
export function useExecutionResult(
	executionId: string | undefined,
	enabled = true,
) {
	return useQuery({
		queryKey: ["executions", executionId, "result"],
		queryFn: () => executionsService.getExecutionResult(executionId!),
		enabled: !!executionId && enabled,
		staleTime: 0, // No caching - always fetch fresh data
	});
}

/**
 * Progressive loading hook: Get only execution logs (admin only)
 */
export function useExecutionLogs(
	executionId: string | undefined,
	enabled = true,
) {
	return useQuery({
		queryKey: ["executions", executionId, "logs"],
		queryFn: () => executionsService.getExecutionLogs(executionId!),
		enabled: !!executionId && enabled,
		staleTime: 0, // No caching - always fetch fresh data
		refetchOnMount: true,
	});
}

/**
 * Progressive loading hook: Get only execution variables (admin only)
 */
export function useExecutionVariables(
	executionId: string | undefined,
	enabled = true,
) {
	return useQuery({
		queryKey: ["executions", executionId, "variables"],
		queryFn: () => executionsService.getExecutionVariables(executionId!),
		enabled: !!executionId && enabled,
		staleTime: 0, // No caching - always fetch fresh data
	});
}
