import { useQuery } from "@tanstack/react-query";
import {
	metricsService,
	type ResourceMetricsResponse,
	type OrganizationMetricsResponse,
	type WorkflowMetricsResponse,
} from "@/services/metrics";

/**
 * Hook for fetching resource usage trends (memory, CPU)
 * Platform admin only
 */
export function useResourceMetrics(days: number = 7, enabled: boolean = true) {
	return useQuery<ResourceMetricsResponse>({
		queryKey: ["resource-metrics", days],
		queryFn: () => metricsService.getResourceMetrics(days),
		enabled,
		staleTime: 60000, // 1 minute
		refetchInterval: 60000,
	});
}

/**
 * Hook for fetching organization breakdown
 * Platform admin only
 */
export function useOrganizationMetrics(
	days: number = 30,
	limit: number = 10,
	enabled: boolean = true,
) {
	return useQuery<OrganizationMetricsResponse>({
		queryKey: ["organization-metrics", days, limit],
		queryFn: () => metricsService.getOrganizationMetrics(days, limit),
		enabled,
		staleTime: 60000,
		refetchInterval: 60000,
	});
}

/**
 * Hook for fetching workflow-level metrics
 * Platform admin only
 */
export function useWorkflowMetrics(
	days: number = 30,
	sortBy: "executions" | "memory" | "duration" | "cpu" = "executions",
	limit: number = 20,
	enabled: boolean = true,
) {
	return useQuery<WorkflowMetricsResponse>({
		queryKey: ["workflow-metrics", days, sortBy, limit],
		queryFn: () => metricsService.getWorkflowMetrics(days, sortBy, limit),
		enabled,
		staleTime: 60000,
		refetchInterval: 60000,
	});
}
