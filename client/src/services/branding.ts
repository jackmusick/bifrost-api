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
		primary_color: string;
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
		const formData = new FormData();
		formData.append("file", file);

		const response = await authFetch(`/api/branding/logo/${type}`, {
			method: "POST",
			body: formData,
			// Don't set Content-Type header - browser will set it with boundary for multipart/form-data
		});

		if (!response.ok) {
			throw new Error(
				`Failed to upload ${type} logo: ${response.statusText}`,
			);
		}
	},

	/**
	 * Reset a specific logo to default
	 */
	async resetLogo(type: "square" | "rectangle"): Promise<BrandingSettings> {
		const response = await authFetch(`/api/branding/logo/${type}`, {
			method: "DELETE",
			headers: { Accept: "application/json" },
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ error: "Unknown error" }));
			throw new Error(
				error.message ||
					`Failed to reset ${type} logo: ${response.statusText}`,
			);
		}

		return response.json();
	},

	/**
	 * Reset primary color to default
	 */
	async resetColor(): Promise<BrandingSettings> {
		const response = await authFetch("/api/branding/color", {
			method: "DELETE",
			headers: { Accept: "application/json" },
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ error: "Unknown error" }));
			throw new Error(
				error.message ||
					`Failed to reset primary color: ${response.statusText}`,
			);
		}

		return response.json();
	},

	/**
	 * Reset all branding to defaults
	 */
	async resetAll(): Promise<BrandingSettings> {
		const response = await authFetch("/api/branding", {
			method: "DELETE",
			headers: { Accept: "application/json" },
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ error: "Unknown error" }));
			throw new Error(
				error.message ||
					`Failed to reset branding: ${response.statusText}`,
			);
		}

		return response.json();
	},
};
