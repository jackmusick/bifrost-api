import { useMemo } from "react";

/**
 * Client-side search hook for filtering arrays of data
 * Optimized for small datasets (<1000 items)
 *
 * @param data - Array of items to search through
 * @param searchTerm - Search query string
 * @param searchFields - Array of field names or accessor functions to search in
 * @param caseSensitive - Whether to perform case-sensitive search (default: false)
 * @returns Filtered array of items matching the search term
 */
export function useSearch<T>(
	data: T[],
	searchTerm: string,
	searchFields: Array<keyof T | ((item: T) => string)>,
	caseSensitive = false,
): T[] {
	return useMemo(() => {
		// No search term = return all data
		if (!searchTerm || searchTerm.trim() === "") {
			return data;
		}

		const normalizedSearch = caseSensitive
			? searchTerm.trim()
			: searchTerm.trim().toLowerCase();

		return data.filter((item) => {
			// Check if any of the specified fields match the search term
			return searchFields.some((field) => {
				let value: string;

				// Support both field names and accessor functions
				if (typeof field === "function") {
					value = field(item);
				} else {
					const fieldValue = item[field];
					value = fieldValue != null ? String(fieldValue) : "";
				}

				const normalizedValue = caseSensitive
					? value
					: value.toLowerCase();
				return normalizedValue.includes(normalizedSearch);
			});
		});
	}, [data, searchTerm, searchFields, caseSensitive]);
}

/**
 * Multi-field search with field weighting (for future enhancement)
 * Returns items sorted by relevance score
 */
export function useWeightedSearch<T>(
	data: T[],
	searchTerm: string,
	fields: Array<{
		field: keyof T | ((item: T) => string);
		weight?: number;
	}>,
): T[] {
	return useMemo(() => {
		if (!searchTerm || searchTerm.trim() === "") {
			return data;
		}

		const normalizedSearch = searchTerm.trim().toLowerCase();

		// Calculate relevance score for each item
		const scoredItems = data
			.map((item) => {
				let score = 0;

				fields.forEach(({ field, weight = 1 }) => {
					let value: string;

					if (typeof field === "function") {
						value = field(item);
					} else {
						const fieldValue = item[field];
						value = fieldValue != null ? String(fieldValue) : "";
					}

					const normalizedValue = value.toLowerCase();

					// Exact match gets higher score
					if (normalizedValue === normalizedSearch) {
						score += 10 * weight;
					}
					// Starts with search term gets medium score
					else if (normalizedValue.startsWith(normalizedSearch)) {
						score += 5 * weight;
					}
					// Contains search term gets base score
					else if (normalizedValue.includes(normalizedSearch)) {
						score += 1 * weight;
					}
				});

				return { item, score };
			})
			.filter(({ score }) => score > 0)
			.sort((a, b) => b.score - a.score);

		return scoredItems.map(({ item }) => item);
	}, [data, searchTerm, fields]);
}
