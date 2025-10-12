/**
 * Config API service
 */

import { api } from './api'
import type { Config, SetConfigRequest } from '@/types/config'

export const configService = {
  /**
   * Get all configs (global or org-specific)
   */
  async getConfigs(params: { scope?: 'global' | 'org'; orgId?: string }): Promise<Config[]> {
    return api.get<Config[]>('/config', params as Record<string, string>)
  },

  /**
   * Set a config value
   */
  async setConfig(request: SetConfigRequest): Promise<Config> {
    return api.post<Config>('/config', request)
  },

  /**
   * Delete a config
   */
  async deleteConfig(key: string, params: { scope?: 'global' | 'org'; orgId?: string }): Promise<void> {
    return api.delete<void>(`/config/${key}`, params as Record<string, string>)
  },
}
