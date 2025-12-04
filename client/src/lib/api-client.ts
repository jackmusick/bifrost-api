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

		// Authentication via HttpOnly cookie (set by backend on login)
		// No need to manually add Authorization header - cookies are sent automatically
		// For service-to-service auth, clients can still use Authorization: Bearer header

		return request;
	},
	async onResponse({ response }) {
		// Handle 401 Unauthorized - token expired or invalid
		// Only redirect if it's a true authentication failure, not a permission issue
		if (response.status === 401) {
			// Clear session storage (cookies are HttpOnly and handled by backend)
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
		// Clear session storage (cookies are HttpOnly and handled by backend)
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

			// Auth via cookie (sent automatically)

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

			// Auth via cookie (sent automatically)

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

			// Auth via cookie (sent automatically)

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
 * Automatically injects context headers and handles 401 responses
 * Auth is handled via HttpOnly cookies (sent automatically by browser)
 */
export async function authFetch(
	url: string,
	options: RequestInit = {},
): Promise<Response> {
	const headers = new Headers(options.headers);

	// Auth via cookie (sent automatically by browser)
	// No need to manually add Authorization header

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
	// BUT: Don't set Content-Type if body is FormData (browser will set it with boundary)
	if (
		["POST", "PUT", "PATCH"].includes(options.method?.toUpperCase() || "") &&
		!headers.has("Content-Type") &&
		!(options.body instanceof FormData)
	) {
		headers.set("Content-Type", "application/json");
	}

	// Ensure credentials are sent (required for cookies in cross-origin scenarios)
	const response = await fetch(url, {
		...options,
		headers,
		credentials: "same-origin"  // Send cookies for same-origin requests
	});

	// Handle 401 the same way as apiClient
	return handle401Response(response);
}
