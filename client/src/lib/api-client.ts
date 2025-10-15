/**
 * Type-safe API client using openapi-fetch
 * Automatically handles X-Organization-Id and X-User-Id headers from session storage
 */

import createClient from "openapi-fetch";
import type { paths } from "./v1";

// Create base client
export const apiClient = createClient<paths>({
    baseUrl: "/api",
});

// Middleware to automatically inject organization and user context headers
apiClient.use({
    async onRequest({ request }) {
        // Get organization ID from session storage (set by org switcher)
        const orgId = sessionStorage.getItem("selectedOrgId");
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
            const orgId = sessionStorage.getItem("selectedOrgId");
            if (orgId) {
                request.headers.set("X-Organization-Id", orgId);
            }

            request.headers.set("X-User-Id", userId);

            return request;
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
    });

    return client;
}
