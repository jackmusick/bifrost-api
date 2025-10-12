/**
 * Configuration types - re-exported from generated API types
 */

import type { components } from './generated/management-api'

export type ConfigType = components['schemas']['ConfigType']
export type Config = components['schemas']['Config']
export type SetConfigRequest = components['schemas']['SetConfigRequest']
export type IntegrationType = components['schemas']['IntegrationType']
export type IntegrationConfig = components['schemas']['IntegrationConfig']
export type SetIntegrationConfigRequest = components['schemas']['SetIntegrationConfigRequest']

// Re-export ConfigScope type for convenience (it's defined inline in the Config schema)
export type ConfigScope = 'GLOBAL' | 'org'
