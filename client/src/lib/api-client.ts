/**
 * Type-safe API client using openapi-fetch
 * Automatically handles X-Organization-Id and X-User-Id headers from session storage
 */

import createClient from "openapi-fetch";
import type { paths } from "./v1";
import { parseApiError, ApiError } from "./api-error";

// Create base client (internal - don't export directly)
// baseUrl is empty because OpenAPI paths already include /api prefix
const baseClient = createClient<paths>({
	baseUrl: "",
});

// Middleware to automatically inject organization and user context headers
// and handle authentication errors
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

		// Add access token to Authorization header
		const token = localStorage.getItem("bifrost_access_token");
		if (token) {
			request.headers.set("Authorization", `Bearer ${token}`);
		}

		return request;
	},
	async onResponse({ response }) {
		// Handle 401 Unauthorized - token expired or invalid
		// Only redirect if it's a true authentication failure, not a permission issue
		if (response.status === 401) {
			// Clear auth state
			localStorage.removeItem("bifrost_access_token");
			localStorage.removeItem("bifrost_user");
			sessionStorage.removeItem("userId");
			sessionStorage.removeItem("current_org_id");

			// Redirect to login, preserving the current path for return
			const currentPath = window.location.pathname;
			if (currentPath !== "/login" && currentPath !== "/setup") {
				window.location.href = `/login?returnTo=${encodeURIComponent(currentPath)}`;
			}
		}
		// 403 Forbidden = permission issue, don't redirect (user is authenticated)
		// Let the calling code handle displaying an appropriate error message

		return response;
	},
});

/**
 * API client with automatic header injection
 * Use the GET, POST, PUT, PATCH, DELETE methods with openapi-fetch syntax
 * Check result.error to handle errors
 */
export const apiClient = baseClient;

/**
 * Shared 401 handler for all clients
 */
function handle401Response(response: Response): Response {
	if (response.status === 401) {
		// Clear auth state
		localStorage.removeItem("bifrost_access_token");
		localStorage.removeItem("bifrost_user");
		sessionStorage.removeItem("userId");
		sessionStorage.removeItem("current_org_id");

		// Redirect to login, preserving the current path for return
		const currentPath = window.location.pathname;
		if (currentPath !== "/login" && currentPath !== "/setup") {
			window.location.href = `/login?returnTo=${encodeURIComponent(currentPath)}`;
		}
	}
	return response;
}

/**
 * Helper to override organization context for admin operations
 */
export function withOrgContext(orgId: string) {
	const client = createClient<paths>({
		baseUrl: "",
	});

	client.use({
		async onRequest({ request }) {
			request.headers.set("X-Organization-Id", orgId);

			const userId = sessionStorage.getItem("userId");
			if (userId) {
				request.headers.set("X-User-Id", userId);
			}

			const token = localStorage.getItem("bifrost_access_token");
			if (token) {
				request.headers.set("Authorization", `Bearer ${token}`);
			}

			return request;
		},
		async onResponse({ response }) {
			return handle401Response(response);
		},
	});

	return client;
}

/**
 * Helper to override user context for admin operations
 */
export function withUserContext(userId: string) {
	const client = createClient<paths>({
		baseUrl: "",
	});

	client.use({
		async onRequest({ request }) {
			const orgId = sessionStorage.getItem("current_org_id");
			if (orgId) {
				request.headers.set("X-Organization-Id", orgId);
			}

			request.headers.set("X-User-Id", userId);

			const token = localStorage.getItem("bifrost_access_token");
			if (token) {
				request.headers.set("Authorization", `Bearer ${token}`);
			}

			return request;
		},
		async onResponse({ response }) {
			return handle401Response(response);
		},
	});

	return client;
}

/**
 * Helper to set both org and user context (for admin operations)
 */
export function withContext(orgId: string, userId: string) {
	const client = createClient<paths>({
		baseUrl: "",
	});

	client.use({
		async onRequest({ request }) {
			request.headers.set("X-Organization-Id", orgId);
			request.headers.set("X-User-Id", userId);

			const token = localStorage.getItem("bifrost_access_token");
			if (token) {
				request.headers.set("Authorization", `Bearer ${token}`);
			}

			return request;
		},
		async onResponse({ response }) {
			return handle401Response(response);
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

/**
 * Authenticated fetch wrapper for endpoints not in OpenAPI spec
 * Automatically injects auth headers and handles 401 responses
 */
export async function authFetch(
	url: string,
	options: RequestInit = {},
): Promise<Response> {
	const headers = new Headers(options.headers);

	// Add auth token
	const token = localStorage.getItem("bifrost_access_token");
	if (token) {
		headers.set("Authorization", `Bearer ${token}`);
	}

	// Add org context
	const orgId = sessionStorage.getItem("current_org_id");
	if (orgId) {
		headers.set("X-Organization-Id", orgId);
	}

	// Add user context
	const userId = sessionStorage.getItem("userId");
	if (userId) {
		headers.set("X-User-Id", userId);
	}

	// Default to JSON content type for POST/PUT/PATCH
	if (
		["POST", "PUT", "PATCH"].includes(options.method?.toUpperCase() || "") &&
		!headers.has("Content-Type")
	) {
		headers.set("Content-Type", "application/json");
	}

	const response = await fetch(url, { ...options, headers });

	// Handle 401 the same way as apiClient
	if (response.status === 401) {
		localStorage.removeItem("bifrost_access_token");
		localStorage.removeItem("bifrost_user");
		sessionStorage.removeItem("userId");
		sessionStorage.removeItem("current_org_id");

		const currentPath = window.location.pathname;
		if (currentPath !== "/login" && currentPath !== "/setup") {
			window.location.href = `/login?returnTo=${encodeURIComponent(currentPath)}`;
		}
	}

	return response;
}
