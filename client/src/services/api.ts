/**
 * API Client for Bifrost Integrations
 * Handles all HTTP requests with authentication
 */

const API_BASE_URL = import.meta.env["VITE_API_URL"] || "/api";

interface RequestOptions extends RequestInit {
    params?: Record<string, string> | undefined;
    orgId?: string | undefined;
    userId?: string | undefined;
}

export class ApiError extends Error {
    constructor(
        message: string,
        public statusCode: number,
        public response?: unknown
    ) {
        super(message);
        this.name = "ApiError";
    }
}

class ApiClient {
    private baseURL: string;

    constructor(baseURL: string) {
        this.baseURL = baseURL;
    }

    /**
     * DEPRECATED: Organization context is now derived from auth by Management API
     * This method is kept for backward compatibility but does nothing
     */
    setOrgContext(orgId: string | undefined): void {
        // No-op - context is now derived server-side
    }

    /**
     * DEPRECATED: User context is now derived from auth by Management API
     * This method is kept for backward compatibility but does nothing
     */
    setUserContext(userId: string | undefined): void {
        // No-op - context is now derived server-side
    }

    async request<T>(
        endpoint: string,
        options: RequestOptions = {}
    ): Promise<T> {
        const { params, orgId, userId, ...fetchOptions } = options;

        // Build URL with query params
        let url = `${this.baseURL}${endpoint}`;
        if (params) {
            const searchParams = new URLSearchParams(params);
            url += `?${searchParams.toString()}`;
        }

        // Get auth token from localStorage (MSAL stores it)
        const token = localStorage.getItem("msal_token");

        // Get org context directly from localStorage (same source as Zustand store)
        // This avoids timing issues with Zustand rehydration
        let contextOrgId = orgId; // Allow explicit override
        if (!contextOrgId) {
            try {
                const storedScope = localStorage.getItem("msp-automation-org-scope");
                if (storedScope) {
                    const parsed = JSON.parse(storedScope);
                    contextOrgId = parsed.state?.scope?.orgId || null;
                }
            } catch (e) {
                console.error('[api] Error reading scope from localStorage:', e);
            }
        }

        console.log('[api] Request to:', endpoint, '- orgId from localStorage:', contextOrgId, 'override:', orgId)

        const headers: Record<string, string> = {
            "Content-Type": "application/json",
            ...fetchOptions.headers,
        };

        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        // Get user context from sessionStorage (kept for backwards compatibility)
        const sessionUserId = sessionStorage.getItem("current_user_id");
        const contextUserId = userId || sessionUserId;

        if (contextOrgId) {
            headers["X-Organization-Id"] = contextOrgId;
            console.log('[api] Setting X-Organization-Id header to:', contextOrgId)
        } else {
            console.log('[api] No X-Organization-Id header (will use GLOBAL)')
        }
        if (contextUserId) {
            headers["X-User-Id"] = contextUserId;
        }

        const response = await fetch(url, {
            ...fetchOptions,
            credentials: "same-origin", // Include cookies for SWA auth (X-MS-CLIENT-PRINCIPAL)
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({
                error: "Unknown error",
                message: response.statusText,
            }));
            throw new ApiError(
                error.message || "Request failed",
                response.status,
                error
            );
        }

        // Handle 204 No Content responses
        if (response.status === 204) {
            return undefined as T;
        }

        return response.json();
    }

    async get<T>(
        endpoint: string,
        params?: Record<string, string>
    ): Promise<T> {
        return this.request<T>(endpoint, { method: "GET", params });
    }

    async post<T>(
        endpoint: string,
        data?: unknown,
        params?: Record<string, string>
    ): Promise<T> {
        return this.request<T>(endpoint, {
            method: "POST",
            body: JSON.stringify(data),
            params,
        });
    }

    async put<T>(
        endpoint: string,
        data?: unknown,
        params?: Record<string, string>
    ): Promise<T> {
        return this.request<T>(endpoint, {
            method: "PUT",
            body: JSON.stringify(data),
            params,
        });
    }

    async delete<T>(
        endpoint: string,
        params?: Record<string, string>
    ): Promise<T> {
        return this.request<T>(endpoint, { method: "DELETE", params });
    }
}

export const api = new ApiClient(API_BASE_URL);
