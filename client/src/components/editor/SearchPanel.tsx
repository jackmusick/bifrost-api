import { useState, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { EditorSearchForm } from "./EditorSearchForm";
import { SearchResultItem } from "./SearchResultItem";
import {
	searchService,
	type SearchResponse,
	type SearchResult,
} from "@/services/searchService";
import { fileService } from "@/services/fileService";
import { useEditorStore } from "@/stores/editorStore";

/**
 * Search Panel Component
 * VS Code-style file content search with results list
 */
export function SearchPanel({
	onResultOpened,
}: {
	onResultOpened?: () => void;
}) {
	const [query, setQuery] = useState("");
	const [caseSensitive, setCaseSensitive] = useState(false);
	const [useRegex, setUseRegex] = useState(false);
	const [isSearching, setIsSearching] = useState(false);
	const [searchResults, setSearchResults] = useState<SearchResponse | null>(
		null,
	);

	const requestRef = useRef(0);
	const [error, setError] = useState<string | null>(null);
	const [submitted, setSubmitted] = useState({
		query: "",
		caseSensitive: false,
		useRegex: false,
	});

	const openingRef = useRef(false);
	const [openingPath, setOpeningPath] = useState<string | null>(null);
	const [openError, setOpenError] = useState<SearchResult | null>(null);

	const handleSearch = useCallback(async () => {
		if (!query.trim() || isSearching) return;
		const request = ++requestRef.current;
		const options = { query: query.trim(), caseSensitive, useRegex };
		setIsSearching(true);
		setError(null);
		try {
			const response = await searchService.searchFiles({
				query: options.query,
				case_sensitive: caseSensitive,
				is_regex: useRegex,
				include_pattern: "**/*",
				max_results: 1000,
			});
			if (request !== requestRef.current) return;
			setSearchResults(response);
			setSubmitted(options);
		} catch (err) {
			if (request === requestRef.current)
				setError(
					err instanceof Error
						? err.message
						: "Couldn’t search files. Try again.",
				);
		} finally {
			if (request === requestRef.current) setIsSearching(false);
		}
	}, [query, caseSensitive, useRegex, isSearching]);

	const handleResultClick = useCallback(
		async (result: SearchResult) => {
			if (openingRef.current) return;
			openingRef.current = true;
			setOpeningPath(result.file_path);
			setOpenError(null);
			const selectExisting = () => {
				const state = useEditorStore.getState();
				const index = state.tabs.findIndex(
					(tab) => tab.file.path === result.file_path,
				);
				if (index < 0) return false;
				state.setActiveTab(index);
				return true;
			};
			try {
				if (!selectExisting()) {
					const response = await fileService.readFile(
						result.file_path,
					);
					// Another editor action may have opened the file during the read.
					if (!selectExisting())
						useEditorStore.getState().openFileInTab(
							{
								path: result.file_path,
								name:
									result.file_path.split("/").pop() ||
									result.file_path,
								type: "file",
								size: response.size,
								extension: result.file_path.includes(".")
									? result.file_path.substring(
											result.file_path.lastIndexOf("."),
										)
									: null,
								modified: response.modified,
								entity_type: null,
								entity_id: null,
							},
							response.content,
							response.encoding as "utf-8" | "base64",
							response.etag,
						);
				}
				useEditorStore.getState().revealLine(result.line);
				onResultOpened?.();
			} catch {
				setOpenError(result);
			} finally {
				openingRef.current = false;
				setOpeningPath(null);
			}
		},
		[onResultOpened],
	);

	const handleClear = () => {
		requestRef.current++;
		setQuery("");
		setSearchResults(null);
		setError(null);
		setOpenError(null);
		setIsSearching(false);
	};

	return (
		<div className="flex h-full min-h-0 min-w-0 flex-col overflow-y-auto">
			<EditorSearchForm
				query={query}
				caseSensitive={caseSensitive}
				useRegex={useRegex}
				isSearching={isSearching}
				onQueryChange={setQuery}
				onCaseSensitiveChange={setCaseSensitive}
				onUseRegexChange={setUseRegex}
				onSearch={handleSearch}
				onClear={handleClear}
			/>
			{isSearching && (
				<p role="status" className="p-3 text-sm text-muted-foreground">
					Searching files…
				</p>
			)}
			{error && (
				<div className="space-y-2 border-b p-3">
					<p
						role="alert"
						className="text-sm text-destructive [overflow-wrap:anywhere]"
					>
						{error}
					</p>
					<Button
						variant="outline"
						className="min-h-11"
						onClick={handleSearch}
						disabled={isSearching || !query.trim()}
					>
						Retry search
					</Button>
				</div>
			)}
			{openingPath && (
				<p
					role="status"
					className="p-3 text-sm text-muted-foreground [overflow-wrap:anywhere]"
				>
					Opening {openingPath}…
				</p>
			)}
			{openError && (
				<div className="space-y-2 border-b p-3">
					<p
						role="alert"
						className="text-sm text-destructive [overflow-wrap:anywhere]"
					>
						Couldn’t open {openError.file_path}. Your search results
						are still available.
					</p>
					<Button
						variant="outline"
						className="min-h-11"
						disabled={!!openingPath}
						onClick={() => handleResultClick(openError)}
					>
						Retry opening file
					</Button>
				</div>
			)}

			{searchResults ? (
				<section aria-label="Search results" className="min-w-0">
					<p
						role="status"
						className="border-b p-3 text-xs text-muted-foreground [overflow-wrap:anywhere]"
					>
						{searchResults.total_matches} matches for “
						{submitted.query}” · {searchResults.files_searched}{" "}
						files searched
						{searchResults.truncated &&
							". Results limited; narrow your search to see more."}
					</p>
					{searchResults.results.length ? (
						<ul className="divide-y">
							{searchResults.results.map((result, index) => (
								<li
									key={`${result.file_path}-${result.line}-${index}`}
								>
									<SearchResultItem
										result={result}
										disabled={!!openingPath}
										{...submitted}
										onClick={() =>
											handleResultClick(result)
										}
									/>
								</li>
							))}
						</ul>
					) : (
						<p className="p-3 text-sm text-muted-foreground">
							No matches found. Try different text or search
							options.
						</p>
					)}
				</section>
			) : (
				!isSearching &&
				!error && (
					<p className="p-3 text-sm text-muted-foreground">
						Enter text to search across your files.
					</p>
				)
			)}
		</div>
	);
}
