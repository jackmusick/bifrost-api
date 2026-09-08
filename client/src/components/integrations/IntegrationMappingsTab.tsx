import {
	CheckCircle2,
	Plus,
	Link as LinkIcon,
	Settings,
	Unlink,
	PlugZap,
	RefreshCw,
	Loader2,
} from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ManualEntityIdInput } from "./ManualEntityIdInput";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { type IntegrationMapping } from "@/services/integrations";
import { AutoMatchControls } from "@/components/integrations/AutoMatchControls";
import { EntitySelector } from "@/components/integrations/EntitySelector";
import { MatchSuggestionBadge } from "@/components/integrations/MatchSuggestionBadge";
import type { MatchMode, MatchSuggestion, MatchResult } from "@/lib/matching";
import { isExpired } from "@/lib/client-types";

interface MappingFormData {
	organization_id: string;
	entity_id: string;
	entity_name: string;
	oauth_token_id?: string;
	config: Record<string, unknown>;
}

export interface OrgWithMapping {
	id: string;
	name: string;
	mapping?: IntegrationMapping;
	formData: MappingFormData;
}

interface ConfigSchemaField {
	key: string;
	type: string;
	required?: boolean;
}

interface Entity {
	value: string;
	label: string;
}

export type MappingAction = "connect" | "disconnect" | "refresh";

export interface PendingMappingAction {
	orgId: string;
	action: MappingAction;
}

export interface IntegrationMappingsTabProps {
	orgsWithMappings: OrgWithMapping[];
	entities: Entity[];
	isLoadingEntities: boolean;
	isEntitiesError?: boolean;
	isFetchingEntities?: boolean;
	onRetryEntities?: () => void;
	hasDataProvider: boolean;
	hasOAuth: boolean;
	configSchema: ConfigSchemaField[];
	configDefaults: Record<string, unknown> | null | undefined;
	autoMatchSuggestions: Map<string, MatchSuggestion>;
	matchStats: MatchResult["stats"] | null;
	isMatching: boolean;
	isDeletePending: boolean;
	onRunAutoMatch: (mode: MatchMode) => void;
	onAcceptAllSuggestions: () => void;
	onClearSuggestions: () => void;
	onAcceptSuggestion: (orgId: string) => void;
	onRejectSuggestion: (orgId: string) => void;
	onUpdateOrgMapping: (
		orgId: string,
		entityId: string,
		entityName?: string,
	) => void;
	onOpenConfigDialog: (orgId: string) => void;
	onDeleteMapping: (org: OrgWithMapping) => void;
	onConnectMapping: (org: OrgWithMapping) => void;
	onDisconnectMapping: (org: OrgWithMapping) => void;
	onRefreshMapping: (org: OrgWithMapping) => void;
	pendingMappingAction?: PendingMappingAction | null;
}

export function IntegrationMappingsTab({
	orgsWithMappings,
	entities,
	isLoadingEntities,
	isEntitiesError,
	isFetchingEntities = false,
	onRetryEntities,
	hasDataProvider,
	hasOAuth,
	configSchema,
	configDefaults,
	autoMatchSuggestions,
	matchStats,
	isMatching,
	isDeletePending,
	onRunAutoMatch,
	onAcceptAllSuggestions,
	onClearSuggestions,
	onAcceptSuggestion,
	onRejectSuggestion,
	onUpdateOrgMapping,
	onOpenConfigDialog,
	onDeleteMapping,
	onConnectMapping,
	onDisconnectMapping,
	onRefreshMapping,
	pendingMappingAction = null,
}: IntegrationMappingsTabProps) {
	const hasNonDefaultConfig = (org: OrgWithMapping): boolean => {
		if (!org.mapping?.config || !configSchema) return false;

		const defaults = configDefaults ?? {};

		return configSchema.some((field) => {
			const currentValue = org.mapping?.config?.[field.key];
			const defaultValue = defaults[field.key];
			return currentValue !== defaultValue;
		});
	};

	const isActionPending = pendingMappingAction !== null;

	return (
		<Card>
			<CardHeader className="flex flex-col items-start justify-between gap-4 space-y-0 xl:flex-row">
				<div>
					<CardTitle>Organization Mappings</CardTitle>
					<CardDescription>
						Configure how each organization maps to external
						entities
					</CardDescription>
				</div>
				{/* Auto-Match Controls in header */}
				{hasDataProvider && orgsWithMappings.length > 0 && (
					<AutoMatchControls
						onRunAutoMatch={onRunAutoMatch}
						onAcceptAll={onAcceptAllSuggestions}
						onClear={onClearSuggestions}
						matchStats={matchStats}
						hasSuggestions={autoMatchSuggestions.size > 0}
						isMatching={isMatching}
						disabled={
							isLoadingEntities ||
							isEntitiesError ||
							isFetchingEntities
						}
					/>
				)}
			</CardHeader>
			<CardContent>
				{isEntitiesError && (
					<div
						role="alert"
						className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-3 text-sm text-[var(--bf-warning)]"
					>
						<p>
							Unable to load external entities. Retry to select or
							match organizations.
						</p>
						{onRetryEntities && (
							<Button
								type="button"
								variant="outline"
								className="min-h-11"
								disabled={isFetchingEntities}
								onClick={onRetryEntities}
							>
								{isFetchingEntities
									? "Retrying…"
									: "Retry entities"}
							</Button>
						)}
					</div>
				)}
				{orgsWithMappings.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-12 text-center">
						<LinkIcon className="h-12 w-12 text-muted-foreground" />
						<h3 className="mt-4 text-lg font-semibold">
							No organizations available
						</h3>
						<p className="mt-2 text-sm text-muted-foreground">
							Create organizations first to set up mappings
						</p>
					</div>
				) : (
					<>
						{!hasDataProvider && (
							<p className="text-sm text-muted-foreground mb-4">
								No data provider configured — entity IDs must be
								entered manually.
							</p>
						)}
						<ul
							className="divide-y"
							aria-label="Organization mappings"
						>
							{orgsWithMappings.map((org) => {
								// Filter out entities already mapped to other orgs
								const usedEntityIds = orgsWithMappings
									.filter(
										(o) =>
											o.id !== org.id &&
											o.formData.entity_id,
									)
									.map((o) => o.formData.entity_id);
								const availableEntities = entities.filter(
									(e) =>
										e.value === org.formData.entity_id ||
										!usedEntityIds.includes(e.value),
								);

								return (
									<IntegrationMappingRecord
										key={org.id}
										org={org}
										availableEntities={availableEntities}
										hasNonDefaultConfig={hasNonDefaultConfig(
											org,
										)}
										hasDataProvider={hasDataProvider}
										autoMatchSuggestions={
											autoMatchSuggestions
										}
										onAcceptSuggestion={onAcceptSuggestion}
										onRejectSuggestion={onRejectSuggestion}
										onUpdateOrgMapping={onUpdateOrgMapping}
										isLoadingEntities={isLoadingEntities}
										isEntitiesError={isEntitiesError}
										hasOAuth={hasOAuth}
										onRefreshMapping={onRefreshMapping}
										onConnectMapping={onConnectMapping}
										onOpenConfigDialog={onOpenConfigDialog}
										onDisconnectMapping={
											onDisconnectMapping
										}
										onDeleteMapping={onDeleteMapping}
										isDeletePending={isDeletePending}
										pendingMappingAction={
											pendingMappingAction
										}
										isActionPending={isActionPending}
									/>
								);
							})}
						</ul>
					</>
				)}
			</CardContent>
		</Card>
	);
}

function formatTimeUntil(expiresAt: string | null): string {
	if (!expiresAt) return "Expiry unknown";
	const ms = new Date(expiresAt).getTime() - Date.now();
	if (Number.isNaN(ms)) return "Expiry unknown";
	if (ms <= 0) return "Expired";
	const totalMinutes = Math.floor(ms / 60000);
	const days = Math.floor(totalMinutes / (60 * 24));
	const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
	const minutes = totalMinutes % 60;
	if (days > 0) return `Expires in ${days}d ${hours}h`;
	if (hours > 0) return `Expires in ${hours}h ${minutes}m`;
	return `Expires in ${minutes}m`;
}

function ConnectedBadge({
	expiresAt,
	isRefreshing,
	disabled,
	onRefresh,
}: {
	expiresAt: string | null;
	isRefreshing: boolean;
	disabled: boolean;
	onRefresh: () => void;
}) {
	return (
		<div className="flex flex-wrap items-center gap-2">
			<Badge className="border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]">
				Connected
			</Badge>
			<span className="text-xs text-muted-foreground">
				{formatTimeUntil(expiresAt)}
			</span>
			<Button
				type="button"
				variant="outline"
				className="min-h-11"
				disabled={disabled || isRefreshing}
				onClick={onRefresh}
			>
				{isRefreshing ? (
					<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
				) : (
					<RefreshCw className="size-4" />
				)}
				{isRefreshing ? "Refreshing…" : "Refresh token"}
			</Button>
		</div>
	);
}

function getConnectionState(org: OrgWithMapping) {
	const mapping = org.mapping;
	if (!mapping) return "none";
	if (mapping.connection_status === "failed") return "failed";
	if (mapping.connection_status === "expired") return "expired";
	if (mapping.connection_status === "completed") {
		if (
			mapping.connection_expires_at &&
			isExpired(mapping.connection_expires_at)
		) {
			return "expired";
		}
		return "connected";
	}
	return "none";
}

function getConnectionActionLabel(
	state: ReturnType<typeof getConnectionState>,
) {
	if (state === "failed") return "Retry connect";
	if (state === "expired") return "Reconnect";
	return "Connect";
}

function getConnectionActionPendingLabel(
	state: ReturnType<typeof getConnectionState>,
) {
	if (state === "failed") return "Retrying…";
	if (state === "expired") return "Reconnecting…";
	return "Connecting…";
}

function IntegrationMappingRecord({
	org,
	availableEntities,
	hasNonDefaultConfig,
	hasDataProvider,
	autoMatchSuggestions,
	onAcceptSuggestion,
	onRejectSuggestion,
	onUpdateOrgMapping,
	isLoadingEntities,
	isEntitiesError,
	hasOAuth,
	onRefreshMapping,
	onConnectMapping,
	onOpenConfigDialog,
	onDisconnectMapping,
	onDeleteMapping,
	isDeletePending,
	pendingMappingAction,
	isActionPending,
}: Pick<
	IntegrationMappingsTabProps,
	| "hasDataProvider"
	| "autoMatchSuggestions"
	| "onAcceptSuggestion"
	| "onRejectSuggestion"
	| "onUpdateOrgMapping"
	| "isLoadingEntities"
	| "isEntitiesError"
	| "hasOAuth"
	| "onRefreshMapping"
	| "onConnectMapping"
	| "onOpenConfigDialog"
	| "onDisconnectMapping"
	| "onDeleteMapping"
	| "isDeletePending"
	| "pendingMappingAction"
> & {
	org: OrgWithMapping;
	availableEntities: Entity[];
	hasNonDefaultConfig: boolean;
	isActionPending: boolean;
}) {
	const connectionState = getConnectionState(org);
	const isConnectPending =
		pendingMappingAction?.orgId === org.id &&
		pendingMappingAction.action === "connect";
	const isDisconnectPending =
		pendingMappingAction?.orgId === org.id &&
		pendingMappingAction.action === "disconnect";
	const isRefreshPending =
		pendingMappingAction?.orgId === org.id &&
		pendingMappingAction.action === "refresh";
	const isRowLocked = isActionPending || isDeletePending;

	return (
		<li className="grid min-w-0 gap-4 py-5 first:pt-0 last:pb-0 xl:grid-cols-2">
			<h3 className="min-w-0 font-medium [overflow-wrap:anywhere] xl:col-span-2">
				{org.name}
			</h3>
			<fieldset disabled={isRowLocked} className="min-w-0 space-y-2">
				<h4 className="text-xs font-medium text-muted-foreground">
					External entity
				</h4>
				{!hasDataProvider ? (
					<ManualEntityIdInput
						orgId={org.id}
						value={org.formData.entity_id}
						onCommit={onUpdateOrgMapping}
					/>
				) : autoMatchSuggestions.has(org.id) ? (
					<MatchSuggestionBadge
						suggestion={autoMatchSuggestions.get(org.id)!}
						onAccept={() => onAcceptSuggestion(org.id)}
						onReject={() => onRejectSuggestion(org.id)}
					/>
				) : (
					<EntitySelector
						entities={availableEntities}
						value={org.formData.entity_id}
						onChange={(value, label) =>
							onUpdateOrgMapping(org.id, value, label)
						}
						isLoading={isLoadingEntities}
						isError={isEntitiesError}
						placeholder="Select entity..."
					/>
				)}
			</fieldset>
			<section className="min-w-0 space-y-2">
				<h4 className="text-xs font-medium text-muted-foreground">
					Mapping status
				</h4>
				{org.mapping ? (
					<Badge
						variant="default"
						className="border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
					>
						<CheckCircle2 className="h-3 w-3 mr-1" />
						Mapped
					</Badge>
				) : org.formData.entity_id ? (
					<Badge variant="secondary">
						<Plus className="h-3 w-3 mr-1" />
						New
					</Badge>
				) : (
					<Badge variant="outline">Not Mapped</Badge>
				)}
			</section>
			<section className="min-w-0 space-y-2">
				<h4 className="text-xs font-medium text-muted-foreground">
					Connection
				</h4>
				{!hasOAuth ? (
					<span className="text-xs text-muted-foreground">
						OAuth not configured
					</span>
				) : connectionState === "connected" ? (
					<ConnectedBadge
						expiresAt={org.mapping?.connection_expires_at ?? null}
						isRefreshing={isRefreshPending}
						disabled={isRowLocked}
						onRefresh={() => onRefreshMapping(org)}
					/>
				) : connectionState === "failed" ? (
					<div className="space-y-2">
						<Badge variant="destructive">Failed</Badge>
						{org.mapping?.connection_message && (
							<p className="text-sm text-destructive [overflow-wrap:anywhere]">
								{org.mapping.connection_message}
							</p>
						)}
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							disabled={isRowLocked || isConnectPending}
							onClick={() => onConnectMapping(org)}
						>
							{isConnectPending ? (
								<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
							) : null}
							{isConnectPending
								? getConnectionActionPendingLabel(
										connectionState,
									)
								: getConnectionActionLabel(connectionState)}
						</Button>
					</div>
				) : connectionState === "expired" ? (
					<div className="space-y-2">
						<Badge variant="destructive">Expired</Badge>
						<p className="text-sm text-destructive">
							Token expired - reconnect required
						</p>
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							disabled={isRowLocked || isConnectPending}
							onClick={() => onConnectMapping(org)}
						>
							{isConnectPending ? (
								<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
							) : null}
							{isConnectPending
								? getConnectionActionPendingLabel(
										connectionState,
									)
								: getConnectionActionLabel(connectionState)}
						</Button>
					</div>
				) : (
					<Button
						size="sm"
						variant="outline"
						className="min-h-11"
						onClick={() => onConnectMapping(org)}
						disabled={isRowLocked || isConnectPending}
					>
						{isConnectPending ? (
							<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
						) : null}
						{isConnectPending
							? getConnectionActionPendingLabel(connectionState)
							: getConnectionActionLabel(connectionState)}
					</Button>
				)}
			</section>
			<section className="min-w-0 space-y-2">
				<h4 className="text-xs font-medium text-muted-foreground">
					Actions
				</h4>
				<div className="flex flex-wrap gap-2">
					<Button
						size="sm"
						variant="ghost"
						onClick={() => onOpenConfigDialog(org.id)}
						title="Configure"
						disabled={isRowLocked}
						className="relative min-h-11"
					>
						<Settings className="h-4 w-4" /> Configure
						{hasNonDefaultConfig && (
							<span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-primary" />
						)}
					</Button>
					<RecordActionsMenu
						label={`Mapping actions for ${org.name}`}
					>
						{org.mapping?.oauth_token_id && (
							<DropdownMenuItem
								disabled={isRowLocked || isDisconnectPending}
								onSelect={() => onDisconnectMapping(org)}
							>
								<PlugZap className="size-4" />
								{isDisconnectPending
									? "Disconnecting…"
									: "Disconnect"}
							</DropdownMenuItem>
						)}
						<DropdownMenuItem
							variant="destructive"
							disabled={!org.mapping || isRowLocked}
							onSelect={() => onDeleteMapping(org)}
						>
							<Unlink className="size-4" /> Unlink
						</DropdownMenuItem>
					</RecordActionsMenu>
				</div>
			</section>
		</li>
	);
}
