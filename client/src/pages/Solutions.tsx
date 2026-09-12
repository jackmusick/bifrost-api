import { SolutionCounts } from "./solutions/SolutionCounts";
/**
 * Solutions Page
 *
 * Operator home for managing Solution installs. Mirrors the Applications page
 * conventions: grid/table view toggle, search, and the standard Organization
 * filter at the top. Installing goes through the CreateEditSolution dialog
 * (opened by the + button → a From-repo / From-zip source picker, prefilled by
 * dropping a .zip anywhere on the page, or deep-linked into the From-repo form
 * via `?repo=<url>&path=<subpath>&ref=<ref>`). Uninstall lives on the
 * individual Solution page.
 */

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
	ArrowUp,
	Boxes,
	Building2,
	GitBranch,
	Globe,
	HardDriveUpload,
	LayoutGrid,
	Plus,
	PowerOff,
	Table as TableIcon,
	Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ListLoadError } from "@/components/layout/ListLoadError";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { SearchBox } from "@/components/search/SearchBox";
import { EntityLogo } from "@/components/EntityLogo";
import { OrganizationSelect } from "@/components/forms/OrganizationSelect";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { ListToolbar } from "@/components/layout/ListToolbar";
import {
	PageScrollArea,
	PageWorkspace,
} from "@/components/layout/PageWorkspace";
import {
	CreateEditSolution,
	type CreateEditSolutionMode,
} from "@/components/solutions/CreateEditSolution";
import { useSearch } from "@/hooks/useSearch";
import { useOrganizations } from "@/hooks/useOrganizations";
import { listSolutions, type Solution } from "@/services/solutions";

export function Solutions() {
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const dragDepth = useRef(0);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const [isDragging, setIsDragging] = useState(false);
	const isDesktop = useIsDesktop();
	const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
	const [searchTerm, setSearchTerm] = useState("");
	// undefined = all organizations, null = global only, string = one org.
	const [filterOrgId, setFilterOrgId] = useState<string | null | undefined>(
		undefined,
	);
	// By default inactive installs are hidden; the toggle surfaces them.
	const [showInactive, setShowInactive] = useState(false);
	// Deep link: `?repo=<url>&path=<subpath>&ref=<ref>` opens the install dialog
	// in From-repository mode with the fields pre-filled. The dialog mode is
	// seeded from the URL on first render; the params are then stripped (in an
	// effect, an external-system update) so a refresh/back doesn't re-open it.
	const [dialogMode, setDialogMode] = useState<CreateEditSolutionMode | null>(
		() => {
			const repo = searchParams.get("repo");
			if (!repo) return null;
			return {
				kind: "create",
				source: "repo",
				repo: {
					url: repo,
					subpath: searchParams.get("path"),
					ref: searchParams.get("ref"),
				},
			};
		},
	);

	useEffect(() => {
		if (!searchParams.has("repo")) return;
		const next = new URLSearchParams(searchParams);
		next.delete("repo");
		next.delete("path");
		next.delete("ref");
		setSearchParams(next, { replace: true });
	}, [searchParams, setSearchParams]);

	const { data: organizations } = useOrganizations();

	const {
		data: solutionsData,
		isLoading,
		error: listError,
		isFetching,
		refetch,
	} = useQuery({
		queryKey: ["solutions"],
		queryFn: () => listSolutions(),
	});
	const solutions = solutionsData?.solutions ?? [];

	const getOrgName = (orgId: string | null | undefined): string => {
		if (!orgId) return "Global";
		const org = organizations?.find((o) => o.id === orgId);
		return org?.name ?? orgId;
	};

	const scopeFiltered =
		filterOrgId === undefined
			? solutions
			: solutions.filter(
					(sol) => (sol.organization_id ?? null) === filterOrgId,
				);
	// Hide inactive installs unless the toggle is on.
	const activeFiltered = showInactive
		? scopeFiltered
		: scopeFiltered.filter((sol) => sol.status !== "inactive");
	const filtered = useSearch(activeFiltered, searchTerm, ["name", "slug"]);

	// Whole-page drag-and-drop: dropping a .zip opens the install dialog
	// prefilled with that file.
	function handleDragEnter(e: React.DragEvent) {
		if (!e.dataTransfer?.types?.includes("Files")) return;
		e.preventDefault();
		dragDepth.current += 1;
		setIsDragging(true);
	}
	function handleDragOver(e: React.DragEvent) {
		if (!e.dataTransfer?.types?.includes("Files")) return;
		e.preventDefault();
	}
	function handleDragLeave(e: React.DragEvent) {
		e.preventDefault();
		dragDepth.current = Math.max(0, dragDepth.current - 1);
		if (dragDepth.current === 0) setIsDragging(false);
	}
	function handleDrop(e: React.DragEvent) {
		e.preventDefault();
		dragDepth.current = 0;
		setIsDragging(false);
		const file = e.dataTransfer?.files?.[0];
		if (file) setDialogMode({ kind: "create", file });
	}

	function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
		const file = e.currentTarget.files?.[0];
		e.currentTarget.value = "";
		if (file) setDialogMode({ kind: "create", file });
	}

	function statusBadge(sol: Solution) {
		if (sol.status !== "inactive") return null;
		return (
			<Badge
				variant="secondary"
				className="gap-1 border-muted-foreground/30 text-muted-foreground"
				data-testid="inactive-badge"
			>
				<PowerOff className="h-3 w-3" />
				Inactive
			</Badge>
		);
	}

	function sourceBadge(sol: Solution) {
		return (
			<Badge variant="secondary" className="gap-1">
				{sol.git_connected ? (
					<GitBranch className="h-3 w-3" />
				) : (
					<HardDriveUpload className="h-3 w-3" />
				)}
				{sol.git_connected ? "Git" : "Manual"}
			</Badge>
		);
	}

	function updateBadge(sol: Solution) {
		if (!sol.update_available_version) return null;
		return (
			<Badge
				variant="default"
				className="gap-1"
				data-testid="update-available-badge"
			>
				<ArrowUp className="h-3 w-3" />v{sol.update_available_version}
			</Badge>
		);
	}

	function orgBadge(sol: Solution) {
		return (
			<Badge variant="outline" className="gap-1">
				{sol.organization_id ? (
					<Building2 className="h-3 w-3" />
				) : (
					<Globe className="h-3 w-3" />
				)}
				{getOrgName(sol.organization_id)}
			</Badge>
		);
	}

	return (
		<PageWorkspace
			data-testid="install-dropzone"
			onDragEnter={handleDragEnter}
			onDragOver={handleDragOver}
			onDragLeave={handleDragLeave}
			onDrop={handleDrop}
			className="relative max-w-7xl mx-auto"
		>
			{/* Drag overlay */}
			{isDragging && (
				<div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center rounded-[var(--bf-radius-surface)] border-2 border-dashed border-primary bg-background/80 backdrop-blur-sm">
					<div className="flex flex-col items-center gap-3 text-primary">
						<Upload className="h-10 w-10" />
						<p className="text-lg font-semibold">
							Drop a Solution .zip to install
						</p>
					</div>
				</div>
			)}

			<ListPageHeader
				title="Solutions"
				description="Installed Solution packages"
				actions={
					<>
						<input
							ref={fileInputRef}
							type="file"
							accept=".zip,application/zip,application/x-zip-compressed"
							className="hidden"
							data-testid="install-file-input"
							onChange={handleFileChange}
						/>
						{isDesktop && (
							<ToggleGroup
								type="single"
								value={viewMode}
								onValueChange={(value: string) =>
									value &&
									setViewMode(value as "grid" | "table")
								}
							>
								<ToggleGroupItem
									value="grid"
									aria-label="Grid view"
									size="lg"
								>
									<LayoutGrid className="h-4 w-4" />
								</ToggleGroupItem>
								<ToggleGroupItem
									value="table"
									aria-label="Table view"
									size="lg"
								>
									<TableIcon className="h-4 w-4" />
								</ToggleGroupItem>
							</ToggleGroup>
						)}
						<Button
							size="lg"
							title="Install Solution"
							data-testid="open-install"
							onClick={() => setDialogMode({ kind: "create" })}
						>
							<Plus className="h-4 w-4" />
							Install Solution
						</Button>
					</>
				}
			/>

			<ListToolbar>
				<SearchBox
					value={searchTerm}
					onChange={setSearchTerm}
					aria-label="Search solutions"
					placeholder="Search name or slug…"
					className="w-full sm:flex-1"
				/>
				<div className="w-full sm:w-64">
					<OrganizationSelect
						value={filterOrgId}
						onChange={setFilterOrgId}
						showAll
						showGlobal
						placeholder="All organizations"
					/>
				</div>
				<div className="flex items-center gap-2 sm:ml-auto">
					<Switch
						id="show-inactive-solutions"
						checked={showInactive}
						onCheckedChange={setShowInactive}
					/>
					<Label
						htmlFor="show-inactive-solutions"
						className="flex min-h-11 cursor-pointer items-center whitespace-nowrap text-sm text-muted-foreground"
					>
						Show Inactive
					</Label>
				</div>
			</ListToolbar>

			<PageScrollArea
				aria-label="Solutions list"
				className={
					isDesktop && viewMode === "table"
						? "space-y-4 lg:flex lg:flex-col lg:overflow-hidden"
						: "space-y-4"
				}
			>
				{listError && (
					<ListLoadError
						resource="Solutions"
						hasCachedData={solutionsData !== undefined}
						isRetrying={isFetching}
						onRetry={() => void refetch()}
					/>
				)}
				{isLoading ? (
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fill,minmax(320px,1fr))]">
						{[...Array(3)].map((_, i) => (
							<Skeleton key={i} className="h-36 w-full" />
						))}
					</div>
				) : listError && !solutionsData ? null : solutions.length ===
				  0 ? (
					<button
						type="button"
						onClick={() => setDialogMode({ kind: "create" })}
						className="flex w-full flex-col items-center justify-center rounded-[var(--bf-radius-surface)] border-2 border-dashed py-20 text-center transition-colors hover:border-primary/60 hover:bg-accent/30"
					>
						<Boxes className="h-12 w-12 text-muted-foreground" />
						<h3 className="mt-4 text-lg font-semibold">
							No Solutions installed yet
						</h3>
						<p className="mt-2 max-w-sm text-sm text-muted-foreground">
							Install from a repository or a .zip — click to
							choose a source, or drag a Solution .zip anywhere on
							this page.
						</p>
					</button>
				) : filtered.length === 0 ? (
					<div className="rounded-[var(--bf-radius-surface)] border py-12 text-center text-sm text-muted-foreground">
						No Solutions match the current filters.
					</div>
				) : !isDesktop || viewMode === "grid" ? (
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fill,minmax(320px,1fr))]">
						{filtered.map((sol) => (
							<Link
								to={`/solutions/${sol.id}`}
								key={sol.id}
								data-testid="install-card"
								className={[
									"group relative flex cursor-pointer flex-col overflow-hidden rounded-[var(--bf-radius-surface)] border transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
									sol.status === "inactive"
										? "bg-muted/40 opacity-70 hover:opacity-100"
										: "bg-card hover:border-border/80 hover:bg-accent/30",
								].join(" ")}
							>
								<div className="flex items-start justify-between gap-3 px-4 py-3">
									<div className="flex min-w-0 items-center gap-2">
										<EntityLogo
											entityType="solution"
											entityId={sol.id}
											logo={sol.logo_url ?? null}
											fallback={
												<Boxes className="h-4 w-4 shrink-0 text-muted-foreground" />
											}
											size={20}
											className="h-5 w-5 rounded object-cover shrink-0"
										/>
										<div className="min-w-0">
											<div className="text-sm font-semibold [overflow-wrap:anywhere]">
												{sol.name}
											</div>
											<div className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
												{sol.slug}
											</div>
										</div>
									</div>
								</div>
								<div className="flex flex-wrap items-center gap-2 border-t px-4 py-2.5">
									{statusBadge(sol)}
									{orgBadge(sol)}
									{sourceBadge(sol)}
									{sol.version && (
										<Badge variant="outline">
											v{sol.version}
										</Badge>
									)}
									{updateBadge(sol)}
								</div>
								<div
									className="mt-auto flex flex-wrap gap-1.5 border-t bg-muted/20 px-4 py-2.5"
									data-testid="solution-card-counts"
								>
									<SolutionCounts solution={sol} />
								</div>
							</Link>
						))}
					</div>
				) : (
					<DataTable className="max-h-full">
						<DataTableHeader>
							<DataTableRow>
								<DataTableHead>Name</DataTableHead>
								<DataTableHead>Slug</DataTableHead>
								<DataTableHead>Status</DataTableHead>
								<DataTableHead>Organization</DataTableHead>
								<DataTableHead>Source</DataTableHead>
								<DataTableHead>Version</DataTableHead>
							</DataTableRow>
						</DataTableHeader>
						<DataTableBody>
							{filtered.map((sol) => (
								<DataTableRow
									key={sol.id}
									data-testid="install-row"
									className="cursor-pointer"
									onClick={() =>
										navigate(`/solutions/${sol.id}`)
									}
								>
									<DataTableCell className="font-medium">
										<Link
											to={`/solutions/${sol.id}`}
											onClick={(event) =>
												event.stopPropagation()
											}
											className="flex min-h-11 items-center gap-2 rounded-[var(--bf-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
										>
											<EntityLogo
												entityType="solution"
												entityId={sol.id}
												logo={sol.logo_url ?? null}
												fallback={
													<Boxes className="h-4 w-4 shrink-0 text-muted-foreground" />
												}
												size={16}
												className="h-4 w-4 rounded object-cover shrink-0"
											/>
											{sol.name}
										</Link>
									</DataTableCell>
									<DataTableCell className="text-muted-foreground">
										{sol.slug}
									</DataTableCell>
									<DataTableCell>
										{statusBadge(sol)}
									</DataTableCell>
									<DataTableCell>
										{orgBadge(sol)}
									</DataTableCell>
									<DataTableCell>
										{sourceBadge(sol)}
									</DataTableCell>
									<DataTableCell className="text-muted-foreground">
										<span className="flex items-center gap-2">
											{sol.version
												? `v${sol.version}`
												: "—"}
											{updateBadge(sol)}
										</span>
									</DataTableCell>
								</DataTableRow>
							))}
						</DataTableBody>
					</DataTable>
				)}
			</PageScrollArea>

			{dialogMode && (
				<CreateEditSolution
					mode={dialogMode}
					open
					onClose={() => setDialogMode(null)}
					onSaved={(sol) => {
						setDialogMode(null);
						navigate(`/solutions/${sol.id}`);
					}}
				/>
			)}
		</PageWorkspace>
	);
}
