/**
 * Data Providers API service
 */

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
   */
  async getOptions(providerName: string, orgId: string): Promise<DataProviderOption[]> {
    // Call workflow engine data provider endpoint directly
    const response = await fetch(`http://localhost:7072/api/data-providers/${providerName}`, {
      method: 'GET',
      headers: {
        'X-Organization-Id': orgId,
      },
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Failed to fetch data provider options')
    }

    const data: DataProviderResponse = await response.json()
    return data.options
  },
}
