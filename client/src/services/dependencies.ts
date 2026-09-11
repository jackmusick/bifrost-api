import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/api-error";
import type { components } from "@/lib/v1";

export type DependencyAvailabilityRequest =
	components["schemas"]["DependencyAvailabilityRequest"];
export type DependencyAvailabilityResponse =
	components["schemas"]["DependencyAvailabilityResponse"];

interface RequestOptions {
	signal?: AbortSignal;
}

export async function getDependencyAvailability(
	request: DependencyAvailabilityRequest,
	options: RequestOptions = {},
): Promise<DependencyAvailabilityResponse> {
	const { data, error } = await apiClient.POST(
		"/api/dependencies/availability",
		{
			body: request,
			signal: options.signal,
		},
	);
	if (error) {
		throw new Error(
			getErrorMessage(error, "Failed to load relationship availability"),
		);
	}
	return data;
}

export function useDependencyAvailability(
	request: DependencyAvailabilityRequest,
	enabled: boolean,
) {
	return useQuery({
		queryKey: ["entity-relationship-availability", request],
		enabled,
		placeholderData: keepPreviousData,
		staleTime: 30_000,
		queryFn: ({ signal }) => getDependencyAvailability(request, { signal }),
	});
}
