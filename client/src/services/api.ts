/**
 * API Client for MSP Automation Platform
 * Handles all HTTP requests with authentication
 */

const API_BASE_URL = import.meta.env['VITE_API_URL'] || '/api'

interface RequestOptions extends RequestInit {
  params?: Record<string, string> | undefined
  orgId?: string | undefined
  userId?: string | undefined
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public response?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
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
    const { params, orgId, userId, ...fetchOptions } = options

    // Build URL with query params
    let url = `${this.baseURL}${endpoint}`
    if (params) {
      const searchParams = new URLSearchParams(params)
      url += `?${searchParams.toString()}`
    }

    // Get auth token from localStorage (MSAL stores it)
    const token = localStorage.getItem('msal_token')

    // Get org and user context from sessionStorage
    const sessionOrgId = sessionStorage.getItem('current_org_id')
    const sessionUserId = sessionStorage.getItem('current_user_id')

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Always add context headers from session (or allow explicit override)
    const contextOrgId = orgId || sessionOrgId
    const contextUserId = userId || sessionUserId

    if (contextOrgId) {
      headers['X-Organization-Id'] = contextOrgId
    }
    if (contextUserId) {
      headers['X-User-Id'] = contextUserId
    }

    const response = await fetch(url, {
      ...fetchOptions,
      credentials: 'same-origin', // Include cookies for SWA auth (X-MS-CLIENT-PRINCIPAL)
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: 'Unknown error',
        message: response.statusText,
      }))
      throw new ApiError(
        error.message || 'Request failed',
        response.status,
        error
      )
    }

    return response.json()
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params })
  }

  async post<T>(endpoint: string, data?: unknown, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      params,
    })
  }

  async put<T>(endpoint: string, data?: unknown, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      params,
    })
  }

  async delete<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', params })
  }
}

export const api = new ApiClient(API_BASE_URL)
