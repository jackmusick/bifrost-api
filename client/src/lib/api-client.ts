/**
 * Type-safe API client using openapi-fetch
 * Automatically handles X-Organization-Id and X-User-Id headers from session storage
 */

import createClient from "openapi-fetch";
import type { paths } from "./v1";
import { parseApiError, ApiError } from "./api-error";

// Create base client (internal - don't export directly)
const baseClient = createClient<paths>({
	baseUrl: "/api",
});

// Middleware to automatically inject organization and user context headers
baseClient.use({
	async onRequest({ request }) {
		// Get organization ID from session storage (set by org switcher)
		const orgId = sessionStorage.getItem("current_org_id");
		if (orgId) {
			request.headers.set("X-Organization-Id", orgId);
		}

		// Get user ID from session storage (set by auth provider)
		const userId = sessionStorage.getItem("userId");
		if (userId) {
			request.headers.set("X-User-Id", userId);
		}

		return request;
	},
});

/**
 * API client with automatic header injection
 * Use the GET, POST, PUT, PATCH, DELETE methods with openapi-fetch syntax
 * Check result.error to handle errors
 */
export const apiClient = baseClient;

/**
 * Helper to override organization context for admin operations
 */
export function withOrgContext(orgId: string) {
	const client = createClient<paths>({
		baseUrl: "/api",
	});

	client.use({
		async onRequest({ request }) {
			request.headers.set("X-Organization-Id", orgId);

			const userId = sessionStorage.getItem("userId");
			if (userId) {
				request.headers.set("X-User-Id", userId);
			}

			return request;
		},
		async onResponse({ response }) {
			return response;
		},
	});

	return client;
}

/**
 * Helper to override user context for admin operations
 */
export function withUserContext(userId: string) {
	const client = createClient<paths>({
		baseUrl: "/api",
	});

	client.use({
		async onRequest({ request }) {
			const orgId = sessionStorage.getItem("current_org_id");
			if (orgId) {
				request.headers.set("X-Organization-Id", orgId);
			}

			request.headers.set("X-User-Id", userId);

			return request;
		},
		async onResponse({ response }) {
			return response;
		},
	});

	return client;
}

/**
 * Helper to set both org and user context (for admin operations)
 */
export function withContext(orgId: string, userId: string) {
	const client = createClient<paths>({
		baseUrl: "/api",
	});

	client.use({
		async onRequest({ request }) {
			request.headers.set("X-Organization-Id", orgId);
			request.headers.set("X-User-Id", userId);
			return request;
		},
		async onResponse({ response }) {
			return response;
		},
	});

	return client;
}

/**
 * Helper to handle openapi-fetch errors
 * Converts the error object to an ApiError with proper message extraction
 */
export function handleApiError(error: unknown): never {
	throw parseApiError(error);
}

// Re-export ApiError for convenience
export { ApiError };
