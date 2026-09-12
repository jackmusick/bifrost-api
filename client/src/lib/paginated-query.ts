type QueryKeySource = {
	queryKey: readonly unknown[];
};

function withoutKeys<T extends Record<string, unknown>>(
	value: T | undefined,
	keys: readonly string[],
) {
	if (!value) return {};
	const result: Record<string, unknown> = { ...value };
	for (const key of keys) {
		delete result[key];
	}
	return result;
}

function stableStringify(value: unknown): string {
	if (Array.isArray(value)) {
		return `[${value.map(stableStringify).join(",")}]`;
	}
	if (value && typeof value === "object") {
		const record = value as Record<string, unknown>;
		return `{${Object.keys(record)
			.sort()
			.map(
				(key) =>
					`${JSON.stringify(key)}:${stableStringify(record[key])}`,
			)
			.join(",")}}`;
	}
	return JSON.stringify(value);
}

function requestFromKey<T>(
	query: QueryKeySource | undefined,
): { params?: { path?: unknown; query?: T }; body?: T } | null {
	if (!query) return null;
	const [, , request] = query.queryKey as [
		string,
		string,
		{ params?: { path?: unknown; query?: T }; body?: T }?,
	];
	return request ?? null;
}

export function sameQueryParamsExcept<T extends Record<string, unknown>>(
	currentParams: T,
	previousQuery: QueryKeySource | undefined,
	keys: readonly string[],
) {
	const previousParams = requestFromKey<T>(previousQuery)?.params?.query;
	if (!previousParams) return false;
	return (
		stableStringify(withoutKeys(currentParams, keys)) ===
		stableStringify(withoutKeys(previousParams, keys))
	);
}

export function samePathAndBodyExcept<T extends Record<string, unknown>>(
	currentPath: unknown,
	currentBody: T,
	previousQuery: QueryKeySource | undefined,
	keys: readonly string[],
) {
	const previousRequest = requestFromKey<T>(previousQuery);
	if (!previousRequest) return false;
	return (
		stableStringify(currentPath) ===
			stableStringify(previousRequest.params?.path) &&
		stableStringify(withoutKeys(currentBody, keys)) ===
			stableStringify(withoutKeys(previousRequest.body, keys))
	);
}
