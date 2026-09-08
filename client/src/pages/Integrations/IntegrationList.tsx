import { Link } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import type { Integration } from "@/services/integrations";

interface IntegrationListProps {
	integrations: Integration[];
	isDesktop: boolean;
	selectedIds: Set<string>;
	onToggleSelect: (integrationId: string) => void;
	onToggleSelectAll: () => void;
	onOpen: (integrationId: string) => void;
	onEdit: (integrationId: string) => void;
	onDelete: (integration: Integration) => void;
}

function integrationOAuthStatus(integration: Integration) {
	if (!integration.has_oauth_config) {
		return { label: "Not configured", variant: "outline" as const };
	}

	return { label: "Configured", variant: "secondary" as const };
}

function integrationDataProviderLabel(integration: Integration) {
	return integration.list_entities_data_provider_id || "None";
}

function integrationConfigSummary(integration: Integration) {
	const fields = integration.config_schema ?? [];
	return {
		items: fields.slice(0, 2).map((field) => field.key),
		overflow: Math.max(0, fields.length - 2),
	};
}

function IntegrationActions({
	integration,
	onEdit,
	onDelete,
}: {
	integration: Integration;
	onEdit: (integrationId: string) => void;
	onDelete: (integration: Integration) => void;
}) {
	return (
		<RecordActionsMenu label={`${integration.name} actions`}>
			<DropdownMenuItem
				className="min-h-11"
				onSelect={() => onEdit(integration.id)}
			>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11"
				onSelect={() => onDelete(integration)}
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);
}

function IntegrationMobileCard({
	integration,
	selected,
	onToggleSelect,
	onEdit,
	onDelete,
}: {
	integration: Integration;
	selected: boolean;
	onToggleSelect: (integrationId: string) => void;
	onEdit: (integrationId: string) => void;
	onDelete: (integration: Integration) => void;
}) {
	const oauth = integrationOAuthStatus(integration);
	const config = integrationConfigSummary(integration);

	return (
		<Card
			data-testid="integration-card"
			className="min-w-0 border-border/70 bg-card"
		>
			<CardContent className="space-y-4 p-4">
				<div className="flex min-w-0 items-start gap-3">
					<Checkbox
						aria-label={`Select ${integration.name}`}
						checked={selected}
						onCheckedChange={() => onToggleSelect(integration.id)}
					/>
					<div className="min-w-0 flex-1 space-y-2">
						<div className="min-w-0">
							<h3 className="text-base font-semibold [overflow-wrap:anywhere]">
								<Link
									to={`/integrations/${integration.id}`}
									className="inline-flex min-h-11 items-center rounded-[var(--bf-radius-control)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								>
									{integration.name}
								</Link>
							</h3>
						</div>
						<div className="flex flex-wrap gap-2">
							<Badge
								variant="outline"
								className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere]"
							>
								{integrationDataProviderLabel(integration)}
							</Badge>
							<Badge
								variant={oauth.variant}
								className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere]"
							>
								{oauth.label}
							</Badge>
						</div>
					</div>
					<IntegrationActions
						integration={integration}
						onEdit={onEdit}
						onDelete={onDelete}
					/>
				</div>

				<div className="space-y-2 text-sm">
					<div className="space-y-2">
						<span className="text-muted-foreground">
							Config fields
						</span>
						{config.items.length === 0 ? (
							<span className="text-muted-foreground">None</span>
						) : (
							<div className="flex flex-wrap gap-1">
								{config.items.map((field) => (
									<Badge
										key={field}
										variant="secondary"
										className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere] text-xs"
									>
										{field}
									</Badge>
								))}
								{config.overflow > 0 && (
									<Badge
										variant="secondary"
										className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere] text-xs"
									>
										+{config.overflow}
									</Badge>
								)}
							</div>
						)}
					</div>
				</div>
			</CardContent>
		</Card>
	);
}

function IntegrationDesktopTable({
	integrations,
	selectedIds,
	onToggleSelect,
	onToggleSelectAll,
	onOpen,
	onEdit,
	onDelete,
}: IntegrationListProps) {
	const allVisibleSelected =
		integrations.length > 0 &&
		integrations.every((integration) => selectedIds.has(integration.id));
	const partiallySelected =
		integrations.some((integration) => selectedIds.has(integration.id)) &&
		!allVisibleSelected;

	return (
		<div className="min-h-0 flex-1">
			<DataTable className="max-h-full [&_table]:table-fixed">
				<DataTableHeader>
					<DataTableRow>
						<DataTableHead className="w-10">
							<Checkbox
								aria-label="Select all visible integrations"
								checked={
									allVisibleSelected
										? true
										: partiallySelected
											? "indeterminate"
											: false
								}
								onCheckedChange={onToggleSelectAll}
							/>
						</DataTableHead>
						<DataTableHead className="whitespace-normal">
							Name
						</DataTableHead>
						<DataTableHead className="w-[20%] whitespace-normal">
							Data Provider
						</DataTableHead>
						<DataTableHead className="w-[22%] whitespace-normal">
							Config Fields
						</DataTableHead>
						<DataTableHead className="w-[12%] whitespace-normal">
							OAuth Status
						</DataTableHead>
						<DataTableHead className="w-16 text-right" />
					</DataTableRow>
				</DataTableHeader>
				<DataTableBody>
					{integrations.map((integration) => {
						const oauth = integrationOAuthStatus(integration);
						const config = integrationConfigSummary(integration);
						return (
							<DataTableRow
								key={integration.id}
								clickable
								onClick={() => onOpen(integration.id)}
							>
								<DataTableCell>
									<Checkbox
										aria-label={`Select ${integration.name}`}
										checked={selectedIds.has(
											integration.id,
										)}
										onCheckedChange={() =>
											onToggleSelect(integration.id)
										}
										onClick={(event) =>
											event.stopPropagation()
										}
									/>
								</DataTableCell>
								<DataTableCell className="font-medium [overflow-wrap:anywhere]">
									<Link
										to={`/integrations/${integration.id}`}
										onClick={(event) =>
											event.stopPropagation()
										}
										className="rounded-[var(--bf-radius-control)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
									>
										{integration.name}
									</Link>
								</DataTableCell>
								<DataTableCell className="w-[20%] whitespace-normal">
									{integration.list_entities_data_provider_id ? (
										<Badge
											variant="outline"
											className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere]"
										>
											{
												integration.list_entities_data_provider_id
											}
										</Badge>
									) : (
										<span className="text-sm text-muted-foreground">
											None
										</span>
									)}
								</DataTableCell>
								<DataTableCell className="w-[22%] whitespace-normal">
									{config.items.length > 0 ? (
										<div className="flex flex-wrap gap-1">
											{config.items.map((field) => (
												<Badge
													key={field}
													variant="secondary"
													className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere] text-xs"
												>
													{field}
												</Badge>
											))}
											{config.overflow > 0 && (
												<Badge
													variant="secondary"
													className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere] text-xs"
												>
													+{config.overflow}
												</Badge>
											)}
										</div>
									) : (
										<span className="text-sm text-muted-foreground">
											None
										</span>
									)}
								</DataTableCell>
								<DataTableCell className="w-[12%] whitespace-normal">
									<Badge
										variant={oauth.variant}
										className="h-auto max-w-full whitespace-normal [overflow-wrap:anywhere] text-xs"
									>
										{oauth.label}
									</Badge>
								</DataTableCell>
								<DataTableCell
									className="w-16 text-right"
									onClick={(event) => event.stopPropagation()}
								>
									<IntegrationActions
										integration={integration}
										onEdit={onEdit}
										onDelete={onDelete}
									/>
								</DataTableCell>
							</DataTableRow>
						);
					})}
				</DataTableBody>
			</DataTable>
		</div>
	);
}

function IntegrationMobileList({
	integrations,
	selectedIds,
	onToggleSelect,
	onToggleSelectAll,
	onEdit,
	onDelete,
}: IntegrationListProps) {
	const allVisibleSelected =
		integrations.length > 0 &&
		integrations.every((integration) => selectedIds.has(integration.id));
	const partiallySelected =
		integrations.some((integration) => selectedIds.has(integration.id)) &&
		!allVisibleSelected;

	return (
		<div className="min-w-0 space-y-3">
			<label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-[var(--bf-radius-control)] border border-border/70 bg-background px-3 text-sm text-muted-foreground">
				<Checkbox
					aria-label="Select all visible integrations"
					checked={
						allVisibleSelected
							? true
							: partiallySelected
								? "indeterminate"
								: false
					}
					onCheckedChange={onToggleSelectAll}
				/>
				<span>Select all visible</span>
			</label>
			<div className="grid min-w-0 gap-3">
				{integrations.map((integration) => (
					<IntegrationMobileCard
						key={integration.id}
						integration={integration}
						selected={selectedIds.has(integration.id)}
						onToggleSelect={onToggleSelect}
						onEdit={onEdit}
						onDelete={onDelete}
					/>
				))}
			</div>
		</div>
	);
}

export function IntegrationList(props: IntegrationListProps) {
	return props.isDesktop ? (
		<IntegrationDesktopTable {...props} />
	) : (
		<IntegrationMobileList {...props} />
	);
}
