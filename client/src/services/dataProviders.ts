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
   * Auth is handled automatically by SWA via X-MS-CLIENT-PRINCIPAL header
   */
  async getOptions(providerName: string, orgId: string): Promise<DataProviderOption[]> {
    // Call via SWA proxy (not direct to Azure Functions)
    // SWA automatically adds X-MS-CLIENT-PRINCIPAL header from authenticated session
    const response = await fetch(`/api/data-providers/${providerName}`, {
      method: 'GET',
      headers: {
        'X-Organization-Id': orgId,
      },
      credentials: 'same-origin', // Include cookies for SWA auth
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Failed to fetch data provider options')
    }

    const data: DataProviderResponse = await response.json()
    return data.options
  },
}
