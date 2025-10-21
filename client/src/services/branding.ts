/**
 * Branding API service
 */

import type { BrandingSettings } from '@/lib/branding'

export const brandingService = {
  /**
   * Get current branding settings
   */
  async getBranding(): Promise<BrandingSettings> {
    const response = await fetch('/api/branding', {
      headers: {
        'Accept': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch branding: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Update branding settings
   */
  async updateBranding(settings: { primaryColor: string }): Promise<BrandingSettings> {
    const response = await fetch('/api/branding', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(settings),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw new Error(error.message || `Failed to update branding: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Upload logo
   */
  async uploadLogo(type: 'square' | 'rectangle', file: File): Promise<void> {
    const response = await fetch(`/api/branding/logo/${type}`, {
      method: 'POST',
      headers: {
        'Content-Type': file.type,
      },
      body: file,
    })

    if (!response.ok) {
      throw new Error(`Failed to upload ${type} logo: ${response.statusText}`)
    }
  },
}
