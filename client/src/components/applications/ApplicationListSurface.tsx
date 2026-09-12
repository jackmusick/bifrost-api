import {
	AppWindow,
	Building2,
	Code2,
	Eye,
	Globe,
	Pencil,
	PlayCircle,
	Trash2,
} from "lucide-react";

import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { ResourceCatalogCard } from "@/components/catalog/ResourceCatalogCard";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { ResourceIcon } from "@/components/ResourceIcon";
import { PageLoader } from "@/components/PageLoader";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { term, useTerminology } from "@/lib/terminology";
import type { components } from "@/lib/v1";
import { prefetchApplicationDetail } from "@/lib/detail-route-loaders";

export type ApplicationListItem = components["schemas"]["ApplicationPublic"] & {
	app_model?: string | null;
	is_solution_managed?: boolean;
	solution_id?: string | null;
};

export interface ApplicationListSurfaceProps {
	apps: ApplicationListItem[];
	viewMode: "grid" | "table";
	isLoading?: boolean;
	isPlatformAdmin: boolean;
	canManageApps: boolean;
	getOrgName: (orgId: string | null | undefined) => string;
	onLaunch: (app: ApplicationListItem) => void;
	onPreview?: (app: ApplicationListItem) => void;
	onOpenSettings?: (app: ApplicationListItem) => void;
	onOpenCode?: (app: ApplicationListItem) => void;
	onDelete?: (app: ApplicationListItem) => void;
	onCreateEmpty?: () => void;
	emptySearchActive?: boolean;
}

function isV2App(app: ApplicationListItem): boolean {
	return app.app_model === "standalone_v2";
}

function canLaunchApp(app: ApplicationListItem): boolean {
	return app.is_published;
}

function getApplicationPrimaryAction(
	app: ApplicationListItem,
	actions: Pick<ApplicationListSurfaceProps, "onLaunch" | "onPreview">,
) {
	if (canLaunchApp(app)) return () => actions.onLaunch(app);
	if (!isV2App(app) && actions.onPreview)
		return () => actions.onPreview?.(app);
	return undefined;
}

function ApplicationActions({
	app,
	onLaunch,
	onPreview,
	onOpenSettings,
	onOpenCode,
	onDelete,
}: { app: ApplicationListItem } & Pick<
	ApplicationListSurfaceProps,
	"onLaunch" | "onPreview" | "onOpenSettings" | "onOpenCode" | "onDelete"
>) {
	const showPublished = canLaunchApp(app);
	const showPreview =
		!isV2App(app) && app.has_unpublished_changes && onPreview;
	if (
		!showPublished &&
		!showPreview &&
		!onOpenSettings &&
		(!onOpenCode || isV2App(app)) &&
		!onDelete
	)
		return null;
	return (
		<RecordActionsMenu label={`${app.name} actions`}>
			{showPublished && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onLaunch(app)}
				>
					<PlayCircle aria-hidden="true" className="size-4" />
					Open Published
				</DropdownMenuItem>
			)}
			{showPreview && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onPreview?.(app)}
				>
					<Eye aria-hidden="true" className="size-4" />
					Open Preview
				</DropdownMenuItem>
			)}
			{onOpenSettings && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onOpenSettings(app)}
				>
					<Pencil aria-hidden="true" className="size-4" />
					Settings
				</DropdownMenuItem>
			)}
			{!isV2App(app) && onOpenCode && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onOpenCode(app)}
				>
					<Code2 aria-hidden="true" className="size-4" />
					Code editor
				</DropdownMenuItem>
			)}
			{onDelete && (
				<DropdownMenuItem
					variant="destructive"
					className="min-h-11"
					onSelect={() => onDelete(app)}
				>
					<Trash2 aria-hidden="true" className="size-4" />
					Delete
				</DropdownMenuItem>
			)}
		</RecordActionsMenu>
	);
}

export function ApplicationListSurface({
	apps,
	viewMode,
	isLoading = false,
	isPlatformAdmin,
	canManageApps,
	getOrgName,
	onLaunch,
	onPreview,
	onOpenSettings,
	onOpenCode,
	onDelete,
	onCreateEmpty,
	emptySearchActive = false,
}: ApplicationListSurfaceProps) {
	const terminology = useTerminology();
	const renderName = (app: ApplicationListItem) => {
		const open = getApplicationPrimaryAction(app, { onLaunch, onPreview });
		return (
			<button
				type="button"
				disabled={!open}
				onClick={(event) => {
					event.stopPropagation();
					open?.();
				}}
				className="min-h-11 min-w-0 text-left font-semibold [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default disabled:hover:text-foreground"
			>
				{app.name}
			</button>
		);
	};

	if (isLoading) {
		return <PageLoader message="Loading applications…" size="sm" />;
	}

	if (apps.length === 0) {
		return (
			<Card>
				<CardContent className="flex flex-col items-center justify-center py-12 text-center">
					<AppWindow className="h-12 w-12 text-muted-foreground" />
					<h3 className="mt-4 text-lg font-semibold">
						{emptySearchActive
							? `No ${term(terminology, "app", "formalPluralLower")} match your search`
							: `No ${term(terminology, "app", "formalPluralLower")} found`}
					</h3>
					<p className="mt-2 text-sm text-muted-foreground">
						{emptySearchActive
							? "Try adjusting your search term or clear the filter"
							: `No ${term(terminology, "app", "formalPluralLower")} are currently available`}
					</p>
					{canManageApps && !emptySearchActive && onCreateEmpty && (
						<Button
							variant="outline"
							size="icon"
							onClick={onCreateEmpty}
							className="mt-4"
							title={`Create ${term(terminology, "app", "formalSingular")}`}
						>
							<AppWindow className="h-4 w-4" />
						</Button>
					)}
				</CardContent>
			</Card>
		);
	}

	if (viewMode === "table" && canManageApps) {
		return (
			<div className="flex-1 min-h-0">
				<DataTable className="max-h-full">
					<DataTableHeader>
						<DataTableRow>
							{isPlatformAdmin && (
								<DataTableHead className="w-0 whitespace-nowrap">
									Organization
								</DataTableHead>
							)}
							<DataTableHead>Name</DataTableHead>
							<DataTableHead>Description</DataTableHead>
							<DataTableHead className="w-0 whitespace-nowrap">
								Status
							</DataTableHead>
							<DataTableHead className="w-0 whitespace-nowrap text-right" />
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{apps.map((app) => {
							const opensPreview =
								!isV2App(app) &&
								!canLaunchApp(app) &&
								Boolean(onPreview);
							const open = getApplicationPrimaryAction(app, {
								onLaunch,
								onPreview,
							});
							return (
								<DataTableRow
									key={app.id}
									clickable={Boolean(open)}
									onClick={open}
									onPointerEnter={() =>
										prefetchApplicationDetail(
											app,
											opensPreview,
										)
									}
									onFocus={() =>
										prefetchApplicationDetail(
											app,
											opensPreview,
										)
									}
								>
									{isPlatformAdmin && (
										<DataTableCell className="w-0 whitespace-nowrap">
											{app.organization_id ? (
												<Badge
													variant="outline"
													className="text-xs"
												>
													<Building2 className="mr-1 h-3 w-3" />
													{getOrgName(
														app.organization_id,
													)}
												</Badge>
											) : (
												<Badge
													variant="default"
													className="text-xs"
												>
													<Globe className="mr-1 h-3 w-3" />
													Global
												</Badge>
											)}
										</DataTableCell>
									)}
									<DataTableCell className="min-w-0 font-medium">
										<div className="flex min-w-0 flex-1 items-center gap-2">
											<ResourceIcon
												kind="app"
												id={app.id}
												logo={app.logo_url ?? null}
												size="table"
											/>
											{renderName(app)}
										</div>
									</DataTableCell>
									<DataTableCell className="max-w-xs truncate text-muted-foreground">
										{app.description || (
											<span className="italic">
												No description
											</span>
										)}
									</DataTableCell>
									<DataTableCell className="w-0 whitespace-nowrap">
										<div className="flex flex-wrap gap-1">
											{app.is_published && (
												<Badge
													variant="outline"
													className="border-[var(--bf-success)]/20 bg-[var(--bf-success)]/10 text-[var(--bf-success)] text-xs"
												>
													{isV2App(app)
														? "Deployed"
														: "Published"}
												</Badge>
											)}
											{app.has_unpublished_changes && (
												<Badge
													variant="outline"
													className="border-[var(--bf-warning)]/20 bg-[var(--bf-warning)]/10 text-[var(--bf-warning)] text-xs"
												>
													Draft
												</Badge>
											)}
											{!app.is_published &&
												!app.has_unpublished_changes && (
													<Badge
														variant="secondary"
														className="text-xs"
													>
														{isV2App(app)
															? "Not deployed"
															: "Empty"}
													</Badge>
												)}
										</div>
									</DataTableCell>
									<DataTableCell
										className="w-0 whitespace-nowrap text-right"
										onClick={(event) =>
											event.stopPropagation()
										}
									>
										<div className="flex justify-end gap-1">
											<Button
												size="sm"
												className="min-h-11 min-w-11 px-3 sm:min-h-0 sm:min-w-0 sm:px-2"
												onClick={() => onLaunch(app)}
												disabled={!canLaunchApp(app)}
												title={
													!canLaunchApp(app)
														? isV2App(app)
															? "Deploy this App first"
															: "No published version"
														: `Open ${term(terminology, "app", "formalSingularLower")}`
												}
											>
												<PlayCircle className="h-4 w-4" />
											</Button>
											{canManageApps &&
												!isV2App(app) &&
												app.has_unpublished_changes &&
												onPreview && (
													<Button
														variant="ghost"
														size="sm"
														className="min-h-11 min-w-11 px-3 sm:min-h-0 sm:min-w-0 sm:px-2"
														onClick={() =>
															onPreview(app)
														}
														title="Preview draft"
													>
														<Eye className="h-4 w-4" />
													</Button>
												)}
											{app.is_solution_managed && (
												<SolutionManagedBadge
													solutionId={app.solution_id}
												/>
											)}
											{canManageApps &&
												!app.is_solution_managed && (
													<ApplicationActions
														app={app}
														onLaunch={onLaunch}
														onPreview={onPreview}
														onOpenSettings={
															onOpenSettings
														}
														onOpenCode={onOpenCode}
														onDelete={onDelete}
													/>
												)}
										</div>
									</DataTableCell>
								</DataTableRow>
							);
						})}
					</DataTableBody>
				</DataTable>
			</div>
		);
	}

	return (
		<div className="grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,320px),1fr))]">
			{apps.map((app) => {
				const opensPreview =
					!isV2App(app) && !canLaunchApp(app) && Boolean(onPreview);
				const defaultTarget = getApplicationPrimaryAction(app, {
					onLaunch,
					onPreview,
				});
				const orgLabel = isPlatformAdmin
					? app.organization_id
						? getOrgName(app.organization_id)
						: "Global"
					: null;
				return (
					<div
						key={app.id}
						onPointerEnter={() =>
							prefetchApplicationDetail(app, opensPreview)
						}
						onFocus={() =>
							prefetchApplicationDetail(app, opensPreview)
						}
					>
						<ResourceCatalogCard
							icon={
								<ResourceIcon
									kind="app"
									id={app.id}
									logo={app.logo_url ?? null}
									size="card"
									className="border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300 [&_svg]:text-current"
								/>
							}
							title={app.name}
							subtitle={
								<>
									{term(terminology, "app", "formalSingular")}
									<span> · </span>
									{isV2App(app) ? "Code app" : "Legacy app"}
								</>
							}
							description={
								app.description || (
									<span className="italic text-muted-foreground/60">
										No description
									</span>
								)
							}
							action={
								<div className="flex items-center gap-1">
									{app.is_solution_managed ? (
										<SolutionManagedBadge
											solutionId={app.solution_id}
										/>
									) : null}
									{canManageApps ? (
										<ApplicationActions
											app={app}
											onLaunch={onLaunch}
											onPreview={onPreview}
											onOpenSettings={
												app.is_solution_managed
													? undefined
													: onOpenSettings
											}
											onOpenCode={
												app.is_solution_managed
													? undefined
													: onOpenCode
											}
											onDelete={
												app.is_solution_managed
													? undefined
													: onDelete
											}
										/>
									) : null}
								</div>
							}
							footer={
								orgLabel ? (
									<p className="flex min-w-0 items-center gap-2">
										{app.organization_id ? (
											<Building2 className="size-3.5 shrink-0" />
										) : (
											<Globe className="size-3.5 shrink-0" />
										)}
										<span className="truncate">
											{orgLabel}
										</span>
									</p>
								) : undefined
							}
							onOpen={() => defaultTarget?.()}
							disabled={!defaultTarget}
						>
							<div className="flex min-w-0 flex-wrap items-center gap-1.5">
								{app.is_published && (
									<Badge
										variant="outline"
										className="border-[var(--bf-success)]/20 bg-[var(--bf-success)]/10 px-1.5 py-0 text-xs text-[var(--bf-success)]"
									>
										{isV2App(app)
											? "Deployed"
											: "Published"}
									</Badge>
								)}
								{app.has_unpublished_changes && (
									<Badge
										variant="outline"
										className="border-[var(--bf-warning)]/20 bg-[var(--bf-warning)]/10 px-1.5 py-0 text-xs text-[var(--bf-warning)]"
									>
										Draft
									</Badge>
								)}
								{!app.is_published &&
									!app.has_unpublished_changes && (
										<Badge
											variant="secondary"
											className="text-xs"
										>
											{isV2App(app)
												? "Not deployed"
												: "Empty"}
										</Badge>
									)}
							</div>
						</ResourceCatalogCard>
					</div>
				);
			})}
		</div>
	);
}
