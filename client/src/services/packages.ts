/**
 * Package Management API service - fully type-safe with openapi-fetch
 */

import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Type aliases for cleaner code
export type InstalledPackage = components["schemas"]["InstalledPackage"];
export type PackageUpdate = components["schemas"]["PackageUpdate"];
export type InstallPackageRequest =
	components["schemas"]["InstallPackageRequest"];
export type InstalledPackagesResponse =
	components["schemas"]["InstalledPackagesResponse"];
export type PackageUpdatesResponse =
	components["schemas"]["PackageUpdatesResponse"];

export const packagesService = {
	/**
	 * List all installed packages in the workspace
	 */
	async listPackages(): Promise<InstalledPackagesResponse> {
		const { data, error } = await apiClient.GET("/api/packages");
		if (error) throw new Error(`Failed to list packages: ${error}`);
		return data!;
	},

	/**
	 * Check for available updates to installed packages
	 */
	async checkUpdates(): Promise<PackageUpdatesResponse> {
		const { data, error } = await apiClient.GET("/api/packages/updates");
		if (error) throw new Error(`Failed to check updates: ${error}`);
		return data!;
	},

	/**
	 * Install a package or all packages from requirements.txt
	 *
	 * Installation is queued via RabbitMQ and progress is streamed via WebSocket
	 * to the package:{user_id} channel.
	 *
	 * @param packageName - Name of package to install (optional - if not provided, installs from requirements.txt)
	 * @param version - Optional version to install (e.g., "2.31.0")
	 */
	async installPackage(packageName?: string, version?: string) {
		const body: InstallPackageRequest = packageName
			? { package: packageName, version: version ?? null }
			: ({} as InstallPackageRequest);

		const { data, error } = await apiClient.POST("/api/packages/install", {
			body,
		});

		if (error) throw new Error(`Failed to install package: ${error}`);
		return data;
	},
};
