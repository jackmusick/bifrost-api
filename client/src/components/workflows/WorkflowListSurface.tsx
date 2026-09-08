import { Link, useNavigate } from "react-router-dom";
import {
	AlertTriangle,
	Bot,
	Building2,
	Code,
	Code2,
	Database,
	Globe,
	History,
	Loader2,
	Pencil,
	PlayCircle,
	Shield,
	Unlink,
	Users,
	Webhook,
} from "lucide-react";

import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { Skeleton } from "@/components/ui/skeleton";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import type { components } from "@/lib/v1";

type BaseWorkflow = components["schemas"]["WorkflowMetadata"];

export type WorkflowListItem = BaseWorkflow & {
	is_orphaned?: boolean;
	access_level?: "authenticated" | "everyone" | "role_based";
	is_solution_managed?: boolean;
	solution_id?: string | null;
};

export interface WorkflowListSurfaceProps {
	workflows: WorkflowListItem[];
	viewMode: "grid" | "table";
	isLoading?: boolean;
	isPlatformAdmin: boolean;
	canManageWorkflows: boolean;
	getOrgName: (orgId: string | null | undefined) => string;
	hasGlobalKey?: boolean;
	workflowsWithKeys?: Set<string>;
	openingWorkflowId?: string | null;
	onOpenCode?: (workflow: WorkflowListItem) => void;
	onEditScope?: (workflow: WorkflowListItem) => void;
	onEditEndpoint?: (workflow: WorkflowListItem) => void;
	onResolveOrphaned?: (workflow: WorkflowListItem) => void;
	onExecute: (workflow: WorkflowListItem) => void;
	onOpenEmpty?: () => void;
	emptySearchActive?: boolean;
}

function WorkflowTypeBadge({ workflow }: { workflow: WorkflowListItem }) {
	if (workflow.type === "tool") {
		return (
			<Badge
				variant="secondary"
				className="bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
				title={workflow.tool_description || "Available as AI tool"}
			>
				<Bot className="mr-1 h-3 w-3" />
				Tool
			</Badge>
		);
	}
	if (workflow.type === "data_provider") {
		return (
			<Badge
				variant="secondary"
				className="bg-[var(--bf-info-soft)] text-[var(--bf-info)]"
				title="Provides data for forms and apps"
			>
				<Database className="mr-1 h-3 w-3" />
				Data Provider
			</Badge>
		);
	}
	return (
		<Badge variant="secondary" title="Executable workflow">
			<PlayCircle className="mr-1 h-3 w-3" />
			Workflow
		</Badge>
	);
}

function executeLabel(workflow: WorkflowListItem): string {
	if (workflow.type === "tool") return "Test Tool";
	if (workflow.type === "data_provider") return "Preview Data";
	return "Execute Workflow";
}

export function WorkflowListSurface({
	workflows,
	viewMode,
	isLoading = false,
	isPlatformAdmin,
	canManageWorkflows,
	getOrgName,
	hasGlobalKey = false,
	workflowsWithKeys = new Set<string>(),
	openingWorkflowId = null,
	onOpenCode,
	onEditScope,
	onEditEndpoint,
	onResolveOrphaned,
	onExecute,
	onOpenEmpty,
	emptySearchActive = false,
}: WorkflowListSurfaceProps) {
	const navigate = useNavigate();

	const renderActions = (workflow: WorkflowListItem) => (
		<RecordActionsMenu label={`${workflow.name} actions`}>
			<DropdownMenuItem asChild className="min-h-11">
				<Link
					to={`/history?workflow=${encodeURIComponent(workflow.id ?? "")}`}
				>
					<History aria-hidden="true" className="size-4" />
					View history
				</Link>
			</DropdownMenuItem>
			{onOpenCode && (
				<DropdownMenuItem
					className="min-h-11"
					disabled={
						openingWorkflowId === (workflow.id ?? workflow.name)
					}
					onSelect={() => onOpenCode(workflow)}
				>
					{openingWorkflowId === (workflow.id ?? workflow.name) ? (
						<Loader2
							aria-hidden="true"
							className="size-4 animate-spin motion-reduce:animate-none"
						/>
					) : (
						<Code2 aria-hidden="true" className="size-4" />
					)}
					Open in editor
				</DropdownMenuItem>
			)}
			{isPlatformAdmin &&
				canManageWorkflows &&
				!workflow.is_solution_managed &&
				onEditScope && (
					<DropdownMenuItem
						className="min-h-11"
						onSelect={() => onEditScope(workflow)}
					>
						<Pencil aria-hidden="true" className="size-4" />
						Edit organization scope
					</DropdownMenuItem>
				)}
			{workflow.endpoint_enabled && onEditEndpoint && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onEditEndpoint(workflow)}
				>
					<Webhook aria-hidden="true" className="size-4" />
					Edit endpoint
				</DropdownMenuItem>
			)}
			{workflow.is_orphaned && onResolveOrphaned && (
				<DropdownMenuItem
					className="min-h-11"
					onSelect={() => onResolveOrphaned(workflow)}
				>
					<Unlink aria-hidden="true" className="size-4" />
					Resolve missing file
				</DropdownMenuItem>
			)}
		</RecordActionsMenu>
	);

	if (isLoading) {
		return viewMode === "grid" ? (
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,300px),1fr))]">
				{[...Array(6)].map((_, i) => (
					<Skeleton key={i} className="h-56 w-full" />
				))}
			</div>
		) : (
			<div className="space-y-2">
				{[...Array(3)].map((_, i) => (
					<Skeleton key={i} className="h-12 w-full" />
				))}
			</div>
		);
	}

	if (workflows.length === 0) {
		return (
			<Card>
				<CardContent className="flex flex-col items-center justify-center py-12 text-center">
					<Code className="h-12 w-12 text-muted-foreground" />
					<h3 className="mt-4 text-lg font-semibold">
						{emptySearchActive
							? "No workflows match your filters"
							: "No workflows available"}
					</h3>
					<p className="mt-2 text-sm text-muted-foreground">
						{emptySearchActive
							? "Adjust your search or clear the filters to see more workflows."
							: "No workflows have been registered in the workflow engine"}
					</p>
					{!emptySearchActive && onOpenEmpty && (
						<Button
							variant="outline"
							onClick={onOpenEmpty}
							className="mt-4"
						>
							<Code className="mr-2 h-4 w-4" />
							Open editor
						</Button>
					)}
				</CardContent>
			</Card>
		);
	}

	if (viewMode === "table") {
		return (
			<div className="flex-1 min-h-0">
				<DataTable className="max-h-full">
					<DataTableHeader>
						<DataTableRow>
							<DataTableHead>Workflow</DataTableHead>
							<DataTableHead className="w-0 whitespace-nowrap text-right">
								<span className="sr-only">Actions</span>
							</DataTableHead>
						</DataTableRow>
					</DataTableHeader>
					<DataTableBody>
						{workflows.map((workflow) => (
							<DataTableRow
								key={workflow.id ?? workflow.name}
								clickable
								href={`/history?workflow=${encodeURIComponent(workflow.id ?? "")}`}
								onClick={() =>
									navigate(
										`/history?workflow=${encodeURIComponent(workflow.id ?? "")}`,
									)
								}
							>
								<DataTableCell className="min-w-0 whitespace-normal align-top">
									<Link
										to={`/history?workflow=${encodeURIComponent(workflow.id ?? "")}`}
										className="inline-flex min-h-11 min-w-0 items-center font-mono font-medium text-left [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
									>
										{workflow.name}
									</Link>
									<div className="mb-2 flex flex-wrap items-center gap-2">
										<WorkflowTypeBadge
											workflow={workflow}
										/>
										{isPlatformAdmin && (
											<span className="text-xs text-muted-foreground">
												{getOrgName(
													workflow.organization_id,
												)}
											</span>
										)}
										{workflow.is_orphaned && (
											<Badge
												variant="outline"
												className="bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]"
											>
												<Unlink className="mr-1 h-3 w-3" />
												Orphaned
											</Badge>
										)}
									</div>
									<p className="max-w-prose text-sm text-muted-foreground [overflow-wrap:anywhere]">
										{workflow.description ||
											"No description"}
									</p>
								</DataTableCell>
								<DataTableCell
									className="w-0 whitespace-nowrap text-right"
									onClick={(event) => event.stopPropagation()}
								>
									<div className="flex items-center justify-end gap-1">
										{workflow.is_solution_managed && (
											<SolutionManagedBadge
												solutionId={
													workflow.solution_id
												}
											/>
										)}

										<Button
											variant="outline"
											size="sm"
											className="min-h-11"
											onClick={() => onExecute(workflow)}
											aria-label={`${executeLabel(workflow)}: ${workflow.name}`}
										>
											<PlayCircle
												aria-hidden="true"
												className="h-4 w-4"
											/>
											{executeLabel(workflow)}
										</Button>
										{renderActions(workflow)}
									</div>
								</DataTableCell>
							</DataTableRow>
						))}
					</DataTableBody>
				</DataTable>
			</div>
		);
	}

	return (
		<div className="grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,300px),1fr))]">
			{workflows.map((workflow) => (
				<Card
					key={workflow.id ?? workflow.name}
					className="min-w-0 flex flex-col transition-colors hover:border-primary"
				>
					<CardHeader className="min-w-0 pb-2">
						<div className="mb-3 flex flex-wrap items-start justify-between gap-2">
							<div className="flex items-center gap-2">
								<WorkflowTypeBadge workflow={workflow} />
							</div>
							<div className="flex items-center justify-end gap-1">
								{workflow.is_solution_managed && (
									<SolutionManagedBadge
										solutionId={workflow.solution_id}
									/>
								)}
								{renderActions(workflow)}
							</div>
						</div>

						<CardTitle className="min-w-0 [overflow-wrap:anywhere] font-mono text-base">
							<Link
								to={`/history?workflow=${encodeURIComponent(workflow.id ?? "")}`}
								className="inline-flex min-h-11 min-w-0 items-center text-left [overflow-wrap:anywhere] hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							>
								{workflow.name}
							</Link>
						</CardTitle>
						{workflow.description && (
							<CardDescription className="mt-2 min-w-0 [overflow-wrap:anywhere] text-sm">
								{workflow.description}
							</CardDescription>
						)}
					</CardHeader>

					<CardContent className="mt-auto space-y-3 pt-0">
						<div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
							{workflow.category && (
								<span>{workflow.category}</span>
							)}
							{workflow.category &&
								(isPlatformAdmin ||
									workflow.endpoint_enabled ||
									workflow.is_orphaned ||
									workflow.disable_global_key) && (
									<span>·</span>
								)}
							{isPlatformAdmin && (
								<span className="flex items-center gap-1">
									{workflow.organization_id ? (
										<>
											<Building2 className="h-3 w-3" />
											{getOrgName(
												workflow.organization_id,
											)}
										</>
									) : (
										<>
											<Globe className="h-3 w-3" />
											Global
										</>
									)}
								</span>
							)}
							{isPlatformAdmin && workflow.access_level && (
								<>
									<span>·</span>
									<Tooltip>
										<TooltipTrigger asChild>
											<span className="flex items-center gap-1 cursor-help">
												{workflow.access_level ===
												"role_based" ? (
													<>
														<Shield className="h-3 w-3" />
														Roles
													</>
												) : (
													<>
														<Users className="h-3 w-3" />
														{workflow.access_level ===
														"everyone"
															? "Everyone"
															: "Auth"}
													</>
												)}
											</span>
										</TooltipTrigger>
										<TooltipContent>
											{workflow.access_level ===
											"authenticated"
												? "Any signed-in user except external users can execute"
												: workflow.access_level ===
													  "everyone"
													? "Any signed-in user, including external users can execute"
													: "Role-based access required"}
										</TooltipContent>
									</Tooltip>
								</>
							)}
						</div>

						{(workflow.endpoint_enabled ||
							workflow.is_orphaned ||
							workflow.disable_global_key) && (
							<div className="flex min-w-0 flex-wrap items-center gap-1.5">
								{workflow.is_orphaned && (
									<Badge
										variant="outline"
										className="bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]"
										title="This workflow's file no longer exists."
									>
										<Unlink className="mr-1 h-3 w-3" />
										Orphaned
									</Badge>
								)}
								{workflow.endpoint_enabled && (
									<Badge
										variant={
											workflow.public_endpoint
												? "destructive"
												: hasGlobalKey ||
													  workflowsWithKeys.has(
															workflow.name ?? "",
													  )
													? "default"
													: "outline"
										}
										className={`motion-reduce:transition-none ${
											workflow.public_endpoint
												? "bg-[var(--bf-warning-soft)] text-[var(--bf-warning)] border-[var(--bf-warning)]/20"
												: hasGlobalKey ||
													  workflowsWithKeys.has(
															workflow.name ?? "",
													  )
													? "bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
													: "text-muted-foreground hover:bg-accent"
										}`}
										title={
											workflow.public_endpoint
												? "Public webhook endpoint - no authentication required"
												: hasGlobalKey ||
													  workflowsWithKeys.has(
															workflow.name ?? "",
													  )
													? "HTTP endpoint enabled with API key"
													: "HTTP endpoint (no API key configured)"
										}
									>
										{workflow.public_endpoint ? (
											<AlertTriangle className="mr-1 h-3 w-3" />
										) : (
											<Webhook className="mr-1 h-3 w-3" />
										)}
										Endpoint
									</Badge>
								)}
								{workflow.disable_global_key && (
									<Badge
										variant="outline"
										className="bg-[var(--bf-warning-soft)] text-[var(--bf-warning)] border-[var(--bf-warning)]/20"
										title="This workflow only accepts workflow-specific API keys (global keys are disabled)"
									>
										Global Opt-Out
									</Badge>
								)}
							</div>
						)}

						<Button
							className="min-h-11 w-full"
							onClick={() => onExecute(workflow)}
						>
							<PlayCircle className="mr-2 h-4 w-4" />
							{executeLabel(workflow)}
						</Button>
					</CardContent>
				</Card>
			))}
		</div>
	);
}
