/**
 * Editor Search API service
 * VS Code-style file content search
 * Local types defined since search endpoints aren't in OpenAPI spec
 */

// Define local types since search models aren't exposed via OpenAPI endpoints
export interface SearchRequest {
	query: string;
	include_pattern?: string | null;
	exclude_pattern?: string | null;
	is_regex?: boolean;
	case_sensitive?: boolean;
	max_results?: number;
}

export interface SearchResult {
	file_path: string;
	line_number: number;
	line_text: string;
	match_start: number;
	match_end: number;
}

export interface SearchResponse {
	results: SearchResult[];
	total_files_searched: number;
	total_matches: number;
	truncated: boolean;
}

export const searchService = {
	/**
	 * Search file contents for text or regex patterns
	 */
	async searchFiles(request: SearchRequest): Promise<SearchResponse> {
		const response = await fetch("/api/editor/search", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
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
