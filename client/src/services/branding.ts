/**
 * Branding API service
 */

import type { BrandingSettings } from "@/lib/branding";
import { authFetch } from "@/lib/api-client";

export const brandingService = {
	/**
	 * Get current branding settings
	 */
	async getBranding(): Promise<BrandingSettings> {
		// Note: This is a public endpoint, but authFetch still works
		const response = await authFetch("/api/branding");

		if (!response.ok) {
			throw new Error(`Failed to fetch branding: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Update branding settings
	 */
	async updateBranding(settings: {
		primaryColor: string;
	}): Promise<BrandingSettings> {
		const response = await authFetch("/api/branding", {
			method: "PUT",
			headers: { Accept: "application/json" },
			body: JSON.stringify(settings),
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ error: "Unknown error" }));
			throw new Error(
				error.message ||
					`Failed to update branding: ${response.statusText}`,
			);
		}

		return response.json();
	},

	/**
	 * Upload logo
	 */
	async uploadLogo(type: "square" | "rectangle", file: File): Promise<void> {
		const response = await authFetch(`/api/branding/logo/${type}`, {
			method: "POST",
			headers: { "Content-Type": file.type },
			body: file,
		});

		if (!response.ok) {
			throw new Error(
				`Failed to upload ${type} logo: ${response.statusText}`,
			);
		}
	},
};
