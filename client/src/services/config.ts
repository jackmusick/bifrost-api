/**
 * Config API service
 * All methods use the centralized api client which automatically handles
 * X-Organization-Id header from sessionStorage
 */

import { api } from './api'
import type { Config, SetConfigRequest } from '@/types/config'

export const configService = {
  /**
   * Get all configs (global or org-specific)
   * Organization context is handled automatically by the api client
   * @param params.scope - Optional scope filter ('global' or 'org')
   */
  async getConfigs(params?: { scope?: 'global' | 'org' }): Promise<Config[]> {
    return api.get<Config[]>('/config', params as Record<string, string>)
  },

  /**
   * Set a config value
   * Organization context is handled automatically by the api client
   */
  async setConfig(request: SetConfigRequest): Promise<Config> {
    return api.post<Config>('/config', request)
  },

  /**
   * Delete a config
   * Organization context is handled automatically by the api client
   * @param key - Config key to delete
   * @param params.scope - Optional scope filter ('global' or 'org')
   */
  async deleteConfig(key: string, params?: { scope?: 'global' | 'org' }): Promise<void> {
    return api.delete<void>(`/config/${key}`, params as Record<string, string>)
  },
}
