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
   * Set organization context for requests
   * Can be called from Zustand store or component
   */
  setOrgContext(orgId: string | undefined): void {
    if (orgId) {
      sessionStorage.setItem('current_org_id', orgId)
    } else {
      sessionStorage.removeItem('current_org_id')
    }
  }

  /**
   * Set user context for requests
   * Can be called from auth store
   */
  setUserContext(userId: string | undefined): void {
    if (userId) {
      sessionStorage.setItem('current_user_id', userId)
    } else {
      sessionStorage.removeItem('current_user_id')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { params, orgId, userId, ...fetchOptions } = options

    // Build URL with query params
    const url = new URL(`${this.baseURL}${endpoint}`)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value)
      })
    }

    // Get auth token from localStorage (MSAL stores it)
    const token = localStorage.getItem('msal_token')

    // Get organization and user context
    const contextOrgId = orgId || sessionStorage.getItem('current_org_id')
    const contextUserId = userId || sessionStorage.getItem('current_user_id')

    const response = await fetch(url.toString(), {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(contextOrgId && { 'X-Organization-Id': contextOrgId }),
        ...(contextUserId && { 'X-User-Id': contextUserId }),
        ...fetchOptions.headers,
      },
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

  async get<T>(endpoint: string, params?: Record<string, string> | undefined): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params: params || undefined })
  }

  async post<T>(endpoint: string, data?: unknown, params?: Record<string, string> | undefined): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      params: params || undefined,
    })
  }

  async put<T>(endpoint: string, data?: unknown, params?: Record<string, string> | undefined): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      params: params || undefined,
    })
  }

  async delete<T>(endpoint: string, params?: Record<string, string> | undefined): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', params: params || undefined })
  }
}

export const api = new ApiClient(API_BASE_URL)
