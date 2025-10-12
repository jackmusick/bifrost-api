/**
 * Secret management type definitions
 */

export interface SecretListResponse {
  secrets: string[]
  orgId?: string
  count: number
}

export interface SecretCreateRequest {
  secretKey: string
  value: string
}

export interface SecretUpdateRequest {
  value: string
}

export interface SecretResponse {
  name: string
  value?: string
  message: string
}

export interface KeyVaultHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  message: string
  vaultUrl?: string
  canConnect: boolean
  canListSecrets: boolean
  canGetSecrets: boolean
  secretCount?: number
  lastChecked: string
}
