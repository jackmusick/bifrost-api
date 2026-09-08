import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { $api } from "@/lib/api-client";
import { Checkbox } from "@/components/ui/checkbox";
import { SettingsResourceNotice } from "./SettingsResourceNotice";

/**
 * AgentMCPConnectionsPanel — per-agent MCP connection grants.
 *
 * Lists every MCP connection in the agent's org with a checkbox. Each
 * checkbox is the grant: ticked means the agent may call any tool that
 * connection publishes; unticked means deny. Tools published by the
 * connection are listed below the checkbox as muted hints so the admin
 * can see what they're granting access to.
 *
 * New agents start with zero grants (deny-by-default). The migration
 * that introduced the join table backfilled grants for agents that
 * existed before the rollout, preserving the legacy "every agent in the
 * org auto-receives every connection's tools" behavior on upgrade.
 *
 * Hidden entirely when the agent has no organization_id — MCP
 * connections are strictly per-org so platform-level agents have
 * nothing to grant.
 */
export function AgentMCPConnectionsPanel({
	organizationId,
	value,
	onChange,
	disabled = false,
}: {
	organizationId: string | null;
	value: string[];
	onChange: (next: string[]) => void;
	disabled?: boolean;
}) {
	// Platform-level agents (no org) cannot carry MCP grants — connections
	// are per-org. Hide the panel entirely rather than show an always-empty
	// list that would confuse admins.
	if (!organizationId) {
		return null;
	}

	return (
		<AgentMCPConnectionsPanelInner
			organizationId={organizationId}
			value={value}
			onChange={onChange}
			disabled={disabled}
		/>
	);
}

function AgentMCPConnectionsPanelInner({
	organizationId,
	value,
	onChange,
	disabled = false,
}: {
	organizationId: string;
	value: string[];
	onChange: (next: string[]) => void;
	disabled?: boolean;
}) {
	// Pull this org's connections + their tool catalogs. The list endpoint
	// returns summaries (no nested tools), so we follow up with
	// per-connection detail fetches. The list is small in practice (1–3
	// connections per org).
	const {
		data: connections = [],
		isError: connectionsError,
		isLoading: connectionsLoading,
		isFetching: connectionsFetching,
		dataUpdatedAt: connectionsUpdated,
		refetch: refetchConnections,
	} = $api.useQuery("get", "/api/mcp-connections", {
		params: { query: { scope: organizationId } },
	});
	const {
		data: servers = [],
		isError: serversError,
		isLoading: serversLoading,
		isFetching: serversFetching,
		dataUpdatedAt: serversUpdated,
		refetch: refetchServers,
	} = $api.useQuery("get", "/api/mcp-servers", {
		params: { query: { active_only: false } },
	});

	const serverNameById = useMemo(() => {
		const map = new Map<string, string>();
		for (const s of servers) map.set(s.id, s.name);
		return map;
	}, [servers]);

	const connectionDetails = useQueries({
		queries: connections.map((c) =>
			$api.queryOptions("get", "/api/mcp-connections/{connection_id}", {
				params: { path: { connection_id: c.id } },
			}),
		),
	});

	const granted = useMemo(() => new Set(value), [value]);

	function toggle(connectionId: string, next: boolean) {
		if (disabled) return;
		if (next) {
			if (granted.has(connectionId)) return;
			onChange([...value, connectionId]);
		} else {
			onChange(value.filter((id) => id !== connectionId));
		}
	}

	if ((connectionsLoading || connectionsError) && !connectionsUpdated)
		return (
			<SettingsResourceNotice
				resource="MCP connections"
				failed={connectionsError}
				loading={connectionsLoading}
				cached={false}
				pending={connectionsFetching}
				onRetry={() => void refetchConnections()}
			/>
		);
	if (connections.length === 0) {
		return (
			<div
				className="rounded-md bg-muted/50 ring-1 ring-foreground/5 p-3 text-xs text-muted-foreground"
				data-testid="agent-mcp-connections-panel-empty"
			>
				<SettingsResourceNotice
					resource="MCP connections"
					failed={connectionsError}
					loading={false}
					cached={!!connectionsUpdated}
					pending={connectionsFetching}
					onRetry={() => void refetchConnections()}
				/>
				This organization has no MCP connections. Add one from the MCP
				servers admin page to grant agents access to external tools.
			</div>
		);
	}

	return (
		<div
			className="rounded-md bg-muted/50 ring-1 ring-foreground/5 p-3 space-y-3"
			data-testid="agent-mcp-connections-panel"
		>
			<SettingsResourceNotice
				resource="MCP connections"
				failed={connectionsError}
				loading={false}
				cached={!!connectionsUpdated}
				pending={connectionsFetching}
				onRetry={() => void refetchConnections()}
			/>
			<SettingsResourceNotice
				resource="MCP servers"
				failed={serversError}
				loading={serversLoading}
				cached={!!serversUpdated}
				pending={serversFetching}
				onRetry={() => void refetchServers()}
			/>
			<div>
				<div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
					External MCP tools
				</div>
				<p className="mt-1 text-xs text-muted-foreground">
					Check each connection this agent should be allowed to call.
					Unchecked connections are denied — the agent will not see
					any of their tools.
				</p>
			</div>
			<div className="space-y-3">
				{connections.map((conn, idx) => {
					const query = connectionDetails[idx];
					const detail = query?.data;
					const tools = detail?.tools ?? [];
					const enabledTools = tools.filter((t) => t.enabled);
					const serverName =
						serverNameById.get(conn.server_id) ?? "MCP server";
					const checked = granted.has(conn.id);
					return (
						<div key={conn.id} className="space-y-2">
							<SettingsResourceNotice
								resource={`tools for ${serverName}`}
								failed={query.isError}
								loading={query.isLoading}
								cached={!!query.dataUpdatedAt}
								pending={query.isFetching}
								onRetry={() => void query.refetch()}
							/>
							<label
								className="flex min-h-11 items-start gap-2 cursor-pointer [overflow-wrap:anywhere]"
								data-testid={`agent-mcp-connection-row-${conn.id}`}
							>
								<Checkbox
									disabled={disabled}
									checked={checked}
									onCheckedChange={(state) =>
										toggle(conn.id, state === true)
									}
									data-testid={`agent-mcp-connection-checkbox-${conn.id}`}
								/>
								<div className="min-w-0 flex-1">
									<div className="text-sm font-medium">
										{serverName}
									</div>
									{!detail &&
									(query.isError ||
										query.isLoading) ? null : enabledTools.length ===
									  0 ? (
										<div className="text-xs text-muted-foreground">
											No tools published yet.
										</div>
									) : (
										<div className="text-xs text-muted-foreground">
											Grants access to:{" "}
											{enabledTools
												.map((t) => t.tool_name)
												.join(", ")}
										</div>
									)}
								</div>
							</label>
						</div>
					);
				})}
			</div>
		</div>
	);
}
