/**
 * React Query client configuration
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			// Don't refetch on window focus by default
			refetchOnWindowFocus: false,
			// Disable retries for all queries
			retry: false,
			// Stale time of 5 minutes by default
			staleTime: 5 * 60 * 1000,
		},
		mutations: {
			// IMPORTANT: Disable retries for ALL mutations globally
			// Mutations are typically NOT idempotent (create, update, delete, execute operations)
			// Retrying failed mutations can cause:
			// - Duplicate workflow executions
			// - Duplicate records created
			// - Unintended side effects
			// If a specific mutation needs retries, it should opt-in explicitly
			retry: false,
		},
	},
});
