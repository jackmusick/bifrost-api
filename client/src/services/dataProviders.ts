/**
 * Data Providers API service
 */

import { api } from './api'

export interface DataProviderOption {
  label: string
  value: string
  metadata?: Record<string, unknown>
}

export interface DataProviderResponse {
  provider: string
  options: DataProviderOption[]
  cached: boolean
  cache_expires_at: string
}

export const dataProvidersService = {
  /**
   * Get options from a data provider
   * Uses the api client which automatically handles X-Organization-Id from session storage
   */
  async getOptions(providerName: string): Promise<DataProviderOption[]> {
    const data = await api.get<DataProviderResponse>(`/data-providers/${providerName}`)
    return data.options
  },
}
