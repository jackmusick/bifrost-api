/**
 * Client-only types that extend or complement the API types
 * These are NOT generated from the OpenAPI spec
 */

import type { components } from './v1'

// ==================== EXECUTION TYPES ====================

export interface ExecutionLog {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  metadata?: Record<string, unknown>
}

export interface ExecutionFilters {
  status?: components['schemas']['ExecutionStatus']
  workflowName?: string
  startDate?: string
  endDate?: string
}

export interface ExecutionListResponse {
  executions: components['schemas']['WorkflowExecution'][]
  total: number
  page: number
  pageSize: number
}

// ==================== FORM TYPES ====================

export interface FormSubmission {
  formId: string
  formData: Record<string, unknown>
}

export interface FormExecutionResponse {
  executionId: string
  status: components['schemas']['ExecutionStatus']
  result?: unknown
  errorMessage?: string
}

// ==================== OAUTH TYPES ====================

export interface OAuthAuthorizeResponse {
  authorization_url: string
  state: string
  message: string
}

export interface OAuthProviderPreset {
  name: string
  displayName: string
  oauth_flow_type: 'authorization_code' | 'client_credentials'
  authorization_url: string
  token_url: string
  default_scopes: string
  documentation_url: string
  icon?: string
}

export const OAUTH_PROVIDER_PRESETS: Record<string, OAuthProviderPreset> = {
  microsoft_graph: {
    name: 'microsoft_graph',
    displayName: 'Microsoft Graph',
    oauth_flow_type: 'authorization_code',
    authorization_url: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    token_url: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
    default_scopes: 'User.Read Mail.Read',
    documentation_url: 'https://learn.microsoft.com/en-us/graph/auth/',
    icon: '🔷',
  },
  google: {
    name: 'google',
    displayName: 'Google APIs',
    oauth_flow_type: 'authorization_code',
    authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth',
    token_url: 'https://oauth2.googleapis.com/token',
    default_scopes: 'https://www.googleapis.com/auth/userinfo.email',
    documentation_url: 'https://developers.google.com/identity/protocols/oauth2',
    icon: '🔴',
  },
  github: {
    name: 'github',
    displayName: 'GitHub',
    oauth_flow_type: 'authorization_code',
    authorization_url: 'https://github.com/login/oauth/authorize',
    token_url: 'https://github.com/login/oauth/access_token',
    default_scopes: 'repo user',
    documentation_url: 'https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps',
    icon: '⚫',
  },
  azure_ad: {
    name: 'azure_ad',
    displayName: 'Azure AD',
    oauth_flow_type: 'client_credentials',
    authorization_url: 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
    token_url: 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
    default_scopes: 'https://graph.microsoft.com/.default',
    documentation_url: 'https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-client-creds-grant-flow',
    icon: '🔷',
  },
}

// OAuth helper functions
export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'green'
    case 'not_connected':
      return 'gray'
    case 'waiting_callback':
    case 'testing':
      return 'yellow'
    case 'failed':
      return 'red'
    default:
      return 'gray'
  }
}

export function getStatusLabel(status: string): string {
  switch (status) {
    case 'completed':
      return 'Connected'
    case 'not_connected':
      return 'Not Connected'
    case 'waiting_callback':
      return 'Waiting for Authorization'
    case 'testing':
      return 'Testing Connection'
    case 'failed':
      return 'Failed'
    default:
      return status
  }
}

export function isExpired(expires_at?: string): boolean {
  if (!expires_at) return true
  return new Date(expires_at) <= new Date()
}

export function expiresSoon(expires_at?: string, hoursThreshold: number = 4): boolean {
  if (!expires_at) return true
  const expiresDate = new Date(expires_at)
  const thresholdDate = new Date(Date.now() + hoursThreshold * 60 * 60 * 1000)
  return expiresDate <= thresholdDate
}

// ==================== TYPE ALIASES ====================

export type ConfigScope = 'GLOBAL' | 'org'
