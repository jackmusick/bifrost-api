/**
 * Editor Search API service
 * VS Code-style file content search
 * Uses auto-generated types from OpenAPI spec
 */

import type { components } from "@/lib/v1";
import { authFetch } from "@/lib/api-client";

// Auto-generated types from OpenAPI spec
export type SearchRequest = components["schemas"]["SearchRequest"];
export type SearchResult = components["schemas"]["SearchResult"];
export type SearchResponse = components["schemas"]["SearchResponse"];

export const searchService = {
	/**
	 * Search file contents for text or regex patterns
	 */
	async searchFiles(request: SearchRequest): Promise<SearchResponse> {
		const response = await authFetch("/api/editor/search", {
			method: "POST",
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({
				error: "Unknown",
				message: response.statusText,
			}));
			throw new Error(
				`Failed to search files: ${error.message || response.statusText}`,
			);
		}

		return response.json();
	},
};
