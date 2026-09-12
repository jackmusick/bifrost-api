/**
 * Dependency Panel
 *
 * Manages npm dependencies for an app. Provides search, add, remove,
 * and version editing. Displayed in the left sidebar of the editor.
 */

import { useState, useCallback, useRef, useEffect, useId } from "react";
import type { KeyboardEvent } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, X, Package, Loader2, AlertCircle } from "lucide-react";
import { useAppDependencies } from "@/hooks/useAppDependencies";
import { searchNpmPackages, type NpmPackageResult } from "@/lib/npm-search";
import { cn } from "@/lib/utils";

interface DependencyPanelProps {
	appId: string;
	/** Solution-managed app: deps are read-only (view, no add/remove). */
	readOnly?: boolean;
}

const MAX_RESULTS = 8;

export function DependencyPanel({
	appId,
	readOnly = false,
}: DependencyPanelProps) {
	const {
		dependencies,
		isLoading,
		isSaving,
		loadError,
		reload,
		addDependency,
		removeDependency,
	} = useAppDependencies(appId);

	const [actionError, setActionError] = useState<string | null>(null);
	const [searchQuery, setSearchQuery] = useState("");
	const [searchResults, setSearchResults] = useState<NpmPackageResult[]>([]);
	const [isSearching, setIsSearching] = useState(false);
	const [showResults, setShowResults] = useState(false);
	const [searchError, setSearchError] = useState<string | null>(null);
	const [activeIndex, setActiveIndex] = useState(-1);
	const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const abortRef = useRef<AbortController | null>(null);
	const requestSeqRef = useRef(0);
	const panelRef = useRef<HTMLDivElement>(null);
	const listboxId = useId();

	const invalidateSearch = useCallback(() => {
		requestSeqRef.current += 1;
		if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
		searchTimerRef.current = null;
		if (abortRef.current) abortRef.current.abort();
		abortRef.current = null;
	}, []);

	const closeSearch = useCallback(() => {
		invalidateSearch();
		setShowResults(false);
		setActiveIndex(-1);
		setIsSearching(false);
	}, [invalidateSearch]);

	// Debounced search
	const handleSearchChange = useCallback(
		(value: string) => {
			invalidateSearch();
			setSearchQuery(value);
			setSearchError(null);
			setActiveIndex(-1);
			setSearchResults([]);
			setIsSearching(false);
			setShowResults(false);

			const trimmed = value.trim();
			if (!trimmed) {
				closeSearch();
				return;
			}

			const requestSeq = requestSeqRef.current;
			searchTimerRef.current = setTimeout(async () => {
				const controller = new AbortController();
				abortRef.current = controller;
				setIsSearching(true);
				setSearchResults([]);
				setShowResults(true);
				setActiveIndex(-1);

				try {
					const results = await searchNpmPackages(
						trimmed,
						MAX_RESULTS,
						controller.signal,
					);
					if (requestSeq !== requestSeqRef.current) return;
					setSearchResults(results);
					setSearchError(null);
					setActiveIndex(results.length > 0 ? 0 : -1);
					setShowResults(true);
				} catch (err) {
					if (requestSeq !== requestSeqRef.current) return;
					if (controller.signal.aborted) return;
					setSearchResults([]);
					setActiveIndex(-1);
					setSearchError(
						err instanceof Error
							? err.message
							: "Could not load npm packages.",
					);
					setShowResults(true);
				} finally {
					if (requestSeq === requestSeqRef.current) {
						setIsSearching(false);
					}
				}
			}, 300);
		},
		[closeSearch, invalidateSearch],
	);

	// Close dropdown when clicking outside
	useEffect(() => {
		function handleClickOutside(e: MouseEvent) {
			if (
				panelRef.current &&
				!panelRef.current.contains(e.target as Node)
			) {
				closeSearch();
			}
		}
		document.addEventListener("mousedown", handleClickOutside);
		return () =>
			document.removeEventListener("mousedown", handleClickOutside);
	}, [closeSearch]);

	// Cleanup timer on unmount
	useEffect(() => {
		return () => {
			if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
			if (abortRef.current) abortRef.current.abort();
		};
	}, []);

	const handleAdd = useCallback(
		async (pkg: NpmPackageResult) => {
			if (isSaving) return;
			setActionError(null);
			try {
				await addDependency(pkg.name, pkg.version);
				closeSearch();
				setSearchQuery("");
				setSearchResults([]);
				setSearchError(null);
			} catch {
				setActionError(
					`Could not add ${pkg.name}. Your search is still available; select the package to retry.`,
				);
			}
		},
		[addDependency, closeSearch, isSaving],
	);

	const handleKeyDown = useCallback(
		(event: KeyboardEvent<HTMLInputElement>) => {
			if (!showResults && event.key !== "Escape") return;
			if (event.key === "Escape") {
				closeSearch();
				return;
			}
			if (!searchResults.length) return;

			if (event.key === "ArrowDown") {
				event.preventDefault();
				setActiveIndex((current) =>
					current < 0 || current >= searchResults.length - 1
						? 0
						: current + 1,
				);
			} else if (event.key === "ArrowUp") {
				event.preventDefault();
				setActiveIndex((current) =>
					current <= 0 ? searchResults.length - 1 : current - 1,
				);
			} else if (event.key === "Enter" && activeIndex >= 0) {
				event.preventDefault();
				void handleAdd(searchResults[activeIndex]);
			}
		},
		[activeIndex, closeSearch, handleAdd, searchResults, showResults],
	);

	const depEntries = Object.entries(dependencies);
	const queryHasText = searchQuery.trim().length > 0;

	if (isLoading) {
		return (
			<div className="p-3 space-y-3">
				<Skeleton className="h-8 w-full" />
				<Skeleton className="h-6 w-3/4" />
				<Skeleton className="h-6 w-1/2" />
			</div>
		);
	}

	if (loadError)
		return (
			<Alert className="m-3 w-auto">
				<AlertDescription className="space-y-3">
					<p>{loadError}</p>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						onClick={reload}
					>
						Retry packages
					</Button>
				</AlertDescription>
			</Alert>
		);
	return (
		<div
			ref={panelRef}
			className="flex min-h-0 flex-1 flex-col rounded-[var(--bf-radius-surface)] border border-border/70 bg-card"
		>
			{actionError && (
				<Alert variant="destructive" className="m-2 w-auto shrink-0">
					<AlertDescription className="[overflow-wrap:anywhere]">
						{actionError}
					</AlertDescription>
				</Alert>
			)}
			{/* Search — hidden for solution-managed (read-only) apps */}
			{!readOnly && (
				<div className="relative shrink-0 border-b p-2">
					<div className="relative">
						<Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
						<Input
							disabled={isSaving}
							role="combobox"
							aria-expanded={showResults}
							aria-haspopup="listbox"
							aria-controls={showResults ? listboxId : undefined}
							aria-activedescendant={
								activeIndex >= 0 &&
								showResults &&
								searchResults[activeIndex]
									? `${listboxId}-option-${activeIndex}`
									: undefined
							}
							aria-label="Search npm packages"
							aria-autocomplete="list"
							value={searchQuery}
							onChange={(e) => handleSearchChange(e.target.value)}
							onFocus={() => {
								if (
									queryHasText &&
									(searchResults.length > 0 ||
										searchError ||
										isSearching)
								) {
									setShowResults(true);
								}
							}}
							onKeyDown={handleKeyDown}
							placeholder="Search npm packages..."
							className="h-11 rounded-[var(--bf-radius-control)] pl-8 pr-8 text-sm"
						/>
						{isSearching && (
							<Loader2 className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 motion-safe:animate-spin text-muted-foreground" />
						)}
					</div>

					{/* Search results dropdown */}
					{showResults && queryHasText && (
						<div
							id={listboxId}
							role="listbox"
							className="absolute left-2 right-2 top-full z-50 mt-1 max-h-64 overflow-auto rounded-[var(--bf-radius-surface)] border border-border/70 bg-popover p-1 shadow-lg ring-1 ring-foreground/5 dark:ring-foreground/10"
						>
							{isSearching ? (
								<div className="flex items-center gap-2 rounded-[var(--bf-radius-surface)] px-3 py-2 text-sm text-muted-foreground">
									<Loader2 className="h-3.5 w-3.5 motion-safe:animate-spin" />
									Searching npm packages…
								</div>
							) : searchError ? (
								<div className="flex items-start gap-2 rounded-[var(--bf-radius-surface)] px-3 py-2 text-sm text-destructive">
									<AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
									<div className="min-w-0">
										<div className="font-medium">
											Could not load npm packages.
										</div>
										<div className="text-xs text-muted-foreground">
											{searchError}
										</div>
									</div>
								</div>
							) : searchResults.length > 0 ? (
								searchResults.map((pkg, index) => {
									const isInstalled =
										pkg.name in dependencies;
									const isActive = index === activeIndex;
									return (
										<button
											key={pkg.name}
											id={`${listboxId}-option-${index}`}
											type="button"
											role="option"
											aria-selected={isActive}
											className={cn(
												"w-full rounded-[var(--bf-radius-surface)] px-3 py-2 text-left text-sm transition-colors",
												"hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
												isActive &&
													"bg-accent text-accent-foreground",
												isInstalled && "opacity-60",
											)}
											onMouseEnter={() =>
												setActiveIndex(index)
											}
											onFocus={() =>
												setActiveIndex(index)
											}
											onClick={() => void handleAdd(pkg)}
											disabled={isInstalled || isSaving}
										>
											<div className="flex min-w-0 items-center justify-between gap-2">
												<span className="min-w-0 truncate font-medium">
													{pkg.name}
												</span>
												<span className="flex-shrink-0 text-xs text-muted-foreground">
													{isInstalled
														? "installed"
														: pkg.version}
												</span>
											</div>
											{pkg.description && (
												<p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
													{pkg.description}
												</p>
											)}
										</button>
									);
								})
							) : (
								<div className="rounded-[var(--bf-radius-surface)] px-3 py-2 text-sm text-muted-foreground">
									No packages found. Try a different npm
									package name.
								</div>
							)}
						</div>
					)}
				</div>
			)}

			{/* Installed packages */}
			<div className="flex-1 overflow-auto">
				{depEntries.length === 0 ? (
					<div className="p-4 text-center text-sm text-muted-foreground">
						<Package className="mx-auto mb-2 h-8 w-8 opacity-30" />
						<p>No packages installed</p>
						<p className="mt-1 text-xs">
							{readOnly
								? "This app is read-only; dependency changes are unavailable."
								: "Search npm packages to add dependencies."}
						</p>
					</div>
				) : (
					<div className="py-1">
						{depEntries.map(([name, version]) => (
							<div
								key={name}
								className="group flex items-center justify-between gap-2 px-3 py-1.5 hover:bg-accent/50"
							>
								<div className="min-w-0">
									<div className="text-sm font-medium [overflow-wrap:anywhere]">
										{name}
									</div>
									<div className="text-xs text-muted-foreground">
										{version}
									</div>
								</div>
								{!readOnly && (
									<Button
										variant="ghost"
										size="icon"
										className={cn("size-11 flex-shrink-0")}
										onClick={() => {
											setActionError(null);
											void removeDependency(name).catch(
												() =>
													setActionError(
														`Could not remove ${name}. It is still installed. Try again.`,
													),
											);
										}}
										disabled={isSaving}
										title={`Remove ${name}`}
										aria-label={`Remove ${name}`}
									>
										<X className="h-3.5 w-3.5" />
									</Button>
								)}
							</div>
						))}
					</div>
				)}
			</div>

			{/* Footer with count */}
			{depEntries.length > 0 && (
				<div className="shrink-0 border-t px-3 py-1.5 text-xs text-muted-foreground">
					{depEntries.length}/20 packages
					{isSaving && (
						<Loader2 className="ml-2 inline-block h-3 w-3 motion-safe:animate-spin" />
					)}
				</div>
			)}
		</div>
	);
}
