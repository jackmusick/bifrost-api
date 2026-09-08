/**
 * UserMCPConnections — "My Connections" tab in user settings (mockup §7).
 *
 * Lists all MCP connections the org admin has set up that the user can
 * opt into for personalized access. Connecting opens an OAuth popup at
 * GET /api/me/mcp-connections/{id}/connect; the popup callback posts
 * back via window.opener.postMessage({type: "mcp_oauth_success", ...})
 * and we invalidate the connection list query.
 *
 * Backend endpoints:
 *   - GET /api/me/mcp-connections lists the caller's per-user credentials
 *     (consent_granted_at, consent_expires_at, granted_scopes) so the row
 *     can show Connected / Not connected and expiration timing.
 *   - DELETE /api/me/mcp-connections/{id} forgets a user_mcp_credentials
 *     row (idempotent: returns 204 whether or not it existed).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useReducedMotion } from "framer-motion";
import { Loader2, Plug, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Skeleton } from "@/components/ui/skeleton";
import { ListLoadError } from "@/components/layout/ListLoadError";
import { $api, apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ConnectionRow {
	connection_id: string;
	server_id: string;
	server_name: string;
	available_in_chat: boolean;
	available_to_autonomous: boolean;
	has_service_token: boolean;
	connected: boolean;
	consent_granted_at: string | null;
	consent_expires_at: string | null;
}

function formatRelativeFromNow(
	iso: string | null,
	kind: "since" | "in",
): string | null {
	if (!iso) return null;
	const t = new Date(iso).getTime();
	const now = Date.now();
	const deltaMs = kind === "since" ? now - t : t - now;
	if (!Number.isFinite(t)) return null;
	if (deltaMs < 0) return kind === "in" ? "expired" : null;
	const days = Math.round(deltaMs / 86400000);
	if (days >= 2)
		return kind === "since" ? `since ${days}d ago` : `in ${days}d`;
	const hours = Math.round(deltaMs / 3600000);
	if (hours >= 2)
		return kind === "since" ? `since ${hours}h ago` : `in ${hours}h`;
	return kind === "since" ? "moments ago" : "soon";
}

function ConnectionActionFeedback({
	message,
	onRetry,
	pending,
	disabled,
	retryLabel = "Retry disconnect",
}: {
	message: string;
	onRetry: () => void;
	pending: boolean;
	disabled: boolean;
	retryLabel?: string;
}) {
	const ref = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (ref.current?.getClientRects().length) {
			ref.current.focus();
			ref.current.scrollIntoView({ block: "nearest" });
		}
	}, [message]);
	return (
		<Alert
			ref={ref}
			tabIndex={-1}
			className="rounded-[var(--bf-radius-surface)] border-destructive/30 bg-destructive/5 p-3"
		>
			<AlertDescription className="flex flex-col items-start gap-2">
				<span className="text-sm text-destructive">{message}</span>
				<Button
					type="button"
					variant="outline"
					className="min-h-11"
					onClick={onRetry}
					disabled={disabled}
				>
					{pending ? "Retrying…" : retryLabel}
				</Button>
			</AlertDescription>
		</Alert>
	);
}

export function UserMCPConnections() {
	const queryClient = useQueryClient();
	const prefersReducedMotion = useReducedMotion();

	// All connections visible to the user (org-scoped on the server side).
	const {
		data: connections = [],
		isLoading: connsLoading,
		isFetching: connsFetching,
		isError: connsIsError,
		refetch,
	} = $api.useQuery("get", "/api/mcp-connections", {
		params: { query: {} },
	});

	// Server templates (so we can label rows with the service name).
	const {
		data: servers = [],
		isLoading: serversLoading,
		isFetching: serversFetching,
		isError: serversIsError,
		refetch: refetchServers,
	} = $api.useQuery("get", "/api/mcp-servers", {
		params: { query: { active_only: false } },
	});

	// The caller's per-user credentials (one row per connection they've connected).
	const {
		data: credentials = [],
		isLoading: credsLoading,
		isFetching: credsFetching,
		isError: credsIsError,
		refetch: refetchCredentials,
	} = $api.useQuery("get", "/api/me/mcp-connections");

	const [pendingDisconnect, setPendingDisconnect] = useState<string | null>(
		null,
	);
	const [pendingConnect, setPendingConnect] = useState<string | null>(null);
	const [disconnectError, setDisconnectError] = useState<{
		connectionId: string;
		message: string;
	} | null>(null);
	const [connectError, setConnectError] = useState<{
		connectionId: string;
		message: string;
	} | null>(null);
	const pendingDisconnectRef = useRef<string | null>(null);
	const pendingConnectRef = useRef<string | null>(null);
	const connectPopupRef = useRef<Window | null>(null);
	const connectPollRef = useRef<number | null>(null);

	const isLoading = connsLoading || serversLoading || credsLoading;
	const isRefreshing = Boolean(
		connsFetching || serversFetching || credsFetching,
	);
	const isError = connsIsError || serversIsError || credsIsError;

	const rows: ConnectionRow[] = useMemo(() => {
		const serverById = new Map<string, string>();
		for (const s of servers) serverById.set(s.id, s.name);
		const credByConn = new Map<string, (typeof credentials)[number]>();
		for (const c of credentials) credByConn.set(c.connection_id, c);
		return connections.map((c) => {
			const cred = credByConn.get(c.id);
			return {
				connection_id: c.id,
				server_id: c.server_id,
				server_name: serverById.get(c.server_id) ?? "Unknown service",
				available_in_chat: c.available_in_chat,
				available_to_autonomous: c.available_to_autonomous,
				has_service_token: c.service_oauth_token_id != null,
				connected: cred != null,
				consent_granted_at: cred?.consent_granted_at ?? null,
				consent_expires_at: cred?.consent_expires_at ?? null,
			};
		});
	}, [connections, servers, credentials]);

	const hasCachedRows = rows.length > 0;

	const retryAll = useCallback(() => {
		void Promise.all([refetch(), refetchServers(), refetchCredentials()]);
	}, [refetch, refetchServers, refetchCredentials]);

	const clearConnectPending = useCallback(() => {
		pendingConnectRef.current = null;
		setPendingConnect(null);
		connectPopupRef.current = null;
		if (connectPollRef.current !== null) {
			window.clearInterval(connectPollRef.current);
			connectPollRef.current = null;
		}
	}, []);

	const failConnect = useCallback(
		(message: string) => {
			const connectionId = pendingConnectRef.current;
			if (connectionId) setConnectError({ connectionId, message });
			connectPopupRef.current?.close();
			clearConnectPending();
		},
		[clearConnectPending],
	);

	// Listen for the popup's success message and invalidate the list. The
	// callback page (api/src/routers/mcp_oauth_callback.py) posts a
	// {type: 'mcp_oauth_success', connection_id} message back to the opener.
	useEffect(() => {
		function handleMessage(ev: MessageEvent) {
			if (ev.origin !== window.location.origin) return;
			const data = ev.data as {
				type?: string;
				connection_id?: string;
			} | null;
			if (!data || typeof data !== "object") return;
			if (data.type === "mcp_oauth_success") {
				if (
					pendingConnectRef.current &&
					data.connection_id !== pendingConnectRef.current
				)
					return;
				toast.success("Connected — your personal access is now linked");
				const popup = connectPopupRef.current;
				popup?.close();
				queryClient.invalidateQueries({
					queryKey: ["get", "/api/mcp-connections"],
				});
				queryClient.invalidateQueries({
					queryKey: ["get", "/api/me/mcp-connections"],
				});
				clearConnectPending();
			} else if (data.type === "mcp_oauth_error") {
				if (
					pendingConnectRef.current &&
					data.connection_id !== pendingConnectRef.current
				)
					return;
				failConnect(
					`Connection failed: ${(data as { error?: string }).error ?? "unknown"}`,
				);
				connectPopupRef.current?.close();
				clearConnectPending();
			}
		}
		window.addEventListener("message", handleMessage);
		return () => {
			window.removeEventListener("message", handleMessage);
			if (connectPollRef.current !== null) {
				window.clearInterval(connectPollRef.current);
				connectPollRef.current = null;
			}
		};
	}, [clearConnectPending, failConnect, queryClient]);

	async function handleConnect(connectionId: string, serverName: string) {
		if (
			isLoading ||
			isError ||
			pendingConnectRef.current ||
			pendingDisconnectRef.current
		)
			return;
		setConnectError(null);
		pendingConnectRef.current = connectionId;
		setPendingConnect(connectionId);
		let keepPending = false;
		try {
			const { data, error } = await apiClient.GET(
				"/api/me/mcp-connections/{connection_id}/connect",
				{ params: { path: { connection_id: connectionId } } },
			);
			if (error || !data?.authorization_url) {
				failConnect(`Failed to start ${serverName} OAuth flow`);
				clearConnectPending();
				return;
			}
			const popup = window.open(
				data.authorization_url,
				"mcp_user_oauth",
				"width=600,height=720",
			);
			if (!popup) {
				failConnect(
					"Popup blocked — please allow popups for this site and try again",
				);
				clearConnectPending();
				return;
			}
			keepPending = true;
			connectPopupRef.current = popup;
			if (connectPollRef.current !== null) {
				window.clearInterval(connectPollRef.current);
			}
			connectPollRef.current = window.setInterval(() => {
				if (popup.closed) {
					failConnect(
						`${serverName} sign-in window closed before completing`,
					);
					clearConnectPending();
				}
			}, 500);
		} catch (err) {
			failConnect(
				err instanceof Error
					? err.message
					: "Failed to start OAuth flow",
			);
		} finally {
			if (!keepPending) clearConnectPending();
		}
	}

	async function handleDisconnect(connectionId: string, serverName: string) {
		if (
			isLoading ||
			isError ||
			pendingDisconnectRef.current ||
			pendingConnectRef.current
		)
			return;
		setDisconnectError((current) =>
			current?.connectionId === connectionId ? null : current,
		);
		pendingDisconnectRef.current = connectionId;
		setPendingDisconnect(connectionId);
		try {
			const { error } = await apiClient.DELETE(
				"/api/me/mcp-connections/{connection_id}",
				{ params: { path: { connection_id: connectionId } } },
			);
			if (error) {
				const message = `Failed to disconnect ${serverName}`;
				setDisconnectError({ connectionId, message });
				return;
			}
			toast.success(`Disconnected from ${serverName}`);
			queryClient.invalidateQueries({
				queryKey: ["get", "/api/me/mcp-connections"],
			});
			setDisconnectError((current) =>
				current?.connectionId === connectionId ? null : current,
			);
		} catch {
			const message = `Failed to disconnect ${serverName}. Try again.`;
			setDisconnectError({ connectionId, message });
		} finally {
			pendingDisconnectRef.current = null;
			setPendingDisconnect(null);
		}
	}

	function renderStatusLabel(row: ConnectionRow) {
		if (credsIsError && credentials.length === 0)
			return <Badge variant="secondary">Status unavailable</Badge>;
		return row.connected ? (
			<>
				<Badge
					variant="default"
					className="bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
				>
					Connected
				</Badge>
				<div className="mt-1 text-xs leading-5 text-muted-foreground [overflow-wrap:anywhere]">
					{[
						formatRelativeFromNow(row.consent_granted_at, "since"),
						row.consent_expires_at
							? `expires ${formatRelativeFromNow(row.consent_expires_at, "in")}`
							: null,
					]
						.filter(Boolean)
						.join(" · ")}
				</div>
			</>
		) : (
			<>
				<Badge variant="secondary">Not connected</Badge>
				<div className="mt-1 text-xs leading-5 text-muted-foreground [overflow-wrap:anywhere]">
					Click Connect to link your account
				</div>
			</>
		);
	}

	function renderConnectionActions(row: ConnectionRow) {
		const isPending =
			isError ||
			pendingConnect !== null ||
			pendingDisconnect !== null ||
			disconnectError?.connectionId === row.connection_id;
		const rowError =
			disconnectError?.connectionId === row.connection_id
				? disconnectError.message
				: null;
		return (
			<div className="space-y-2">
				<div className="flex flex-wrap items-center gap-2">
					<Button
						size="sm"
						className="min-h-11"
						disabled={isPending}
						onClick={() =>
							void handleConnect(
								row.connection_id,
								row.server_name,
							)
						}
					>
						{pendingConnect === row.connection_id
							? "Connecting..."
							: row.connected
								? "Reconnect"
								: "Connect"}
					</Button>
					<Button
						variant="outline"
						size="sm"
						disabled={!row.connected || isPending}
						className="min-h-11 text-[var(--bf-danger)] disabled:text-muted-foreground"
						onClick={() =>
							void handleDisconnect(
								row.connection_id,
								row.server_name,
							)
						}
					>
						{pendingDisconnect === row.connection_id ? (
							<Loader2
								className={cn(
									"h-3 w-3",
									!prefersReducedMotion &&
										"motion-safe:animate-spin",
								)}
							/>
						) : (
							"Disconnect"
						)}
					</Button>
				</div>
				{pendingConnect === row.connection_id && (
					<p role="status" className="text-sm text-muted-foreground">
						Continue sign-in in the popup window.
					</p>
				)}
				{connectError?.connectionId === row.connection_id && (
					<ConnectionActionFeedback
						message={connectError.message}
						retryLabel="Retry connect"
						onRetry={() =>
							void handleConnect(
								row.connection_id,
								row.server_name,
							)
						}
						pending={pendingConnect === row.connection_id}
						disabled={isPending}
					/>
				)}
				{rowError && (
					<ConnectionActionFeedback
						message={rowError}
						onRetry={() =>
							void handleDisconnect(
								row.connection_id,
								row.server_name,
							)
						}
						pending={pendingDisconnect === row.connection_id}
						disabled={
							isError ||
							pendingDisconnect !== null ||
							pendingConnect !== null
						}
					/>
				)}
			</div>
		);
	}

	function fallbackLabel(row: ConnectionRow) {
		if (row.available_in_chat && row.has_service_token) {
			return (
				<>
					<span className="text-foreground">
						Shared service account
					</span>
					<div className="text-xs text-muted-foreground">
						(if you disconnect)
					</div>
				</>
			);
		}
		return (
			<>
				<Badge
					variant="default"
					className="bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]"
				>
					No fallback
				</Badge>
				<div className="text-xs text-muted-foreground">
					{credsIsError && credentials.length === 0
						? "Personal access could not be checked"
						: row.connected
							? "No shared account if you disconnect"
							: "Tools disabled until you connect"}
				</div>
			</>
		);
	}

	return (
		<Card className="rounded-[var(--bf-radius-surface)] border-border/70 bg-card">
			<CardContent className="@container space-y-4 p-4 sm:p-6">
				<div className="flex flex-col items-stretch gap-3 @2xl:flex-row @2xl:items-start @2xl:justify-between">
					<div>
						<h2 className="text-lg font-semibold leading-6">
							My Connections
						</h2>
						<p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
							Connect your account to external tools so agents can
							act with your identity (and your permissions).
							Without a personal connection, the agent uses the
							shared org service account if your admin has enabled
							it.
						</p>
					</div>
					<Button
						variant="outline"
						size="sm"
						className="min-h-11 shrink-0"
						onClick={retryAll}
						disabled={isRefreshing}
						title="Refresh"
					>
						<RefreshCw
							className={cn(
								"mr-1 h-4 w-4",
								isRefreshing &&
									!prefersReducedMotion &&
									"motion-safe:animate-spin",
							)}
						/>
						Refresh
					</Button>
				</div>

				{isLoading ? (
					<div
						className="space-y-2"
						role="status"
						aria-label="Loading MCP connections"
					>
						{[...Array(3)].map((_, i) => (
							<Skeleton
								key={i}
								className="h-20 w-full rounded-[var(--bf-radius-surface)]"
							/>
						))}
					</div>
				) : (
					<>
						{isError && (
							<ListLoadError
								resource="your MCP connections"
								hasCachedData={hasCachedRows}
								isRetrying={isRefreshing}
								onRetry={retryAll}
							/>
						)}
						{rows.length === 0 && !isError ? (
							<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 py-12 text-center">
								<Plug className="mx-auto h-10 w-10 text-muted-foreground" />
								<h3 className="mt-3 font-semibold leading-6">
									No connections available
								</h3>
								<p className="mx-auto mt-1 max-w-md text-sm leading-6 text-muted-foreground">
									No MCP services have been set up for your
									organization yet. Ask an admin to add a
									connection.
								</p>
							</div>
						) : rows.length > 0 ? (
							<>
								<div className="space-y-3 @2xl:hidden">
									{rows.map((row) => (
										<Card
											key={row.connection_id}
											className="rounded-[var(--bf-radius-surface)] border-border/70"
										>
											<CardContent className="space-y-3 p-4">
												<div className="space-y-1.5">
													<p className="text-sm font-medium leading-6 [overflow-wrap:anywhere]">
														{row.server_name}
													</p>
													{renderStatusLabel(row)}
												</div>
												<div className="space-y-2 text-xs leading-5 text-muted-foreground">
													<div>
														<span className="font-medium text-foreground">
															Org default:
														</span>{" "}
														{fallbackLabel(row)}
													</div>
												</div>
												{renderConnectionActions(row)}
											</CardContent>
										</Card>
									))}
								</div>

								<div className="hidden @2xl:block">
									<DataTable>
										<DataTableHeader>
											<DataTableRow>
												<DataTableHead>
													Service
												</DataTableHead>
												<DataTableHead>
													Your status
												</DataTableHead>
												<DataTableHead>
													Org default
												</DataTableHead>
												<DataTableHead className="text-right">
													Actions
												</DataTableHead>
											</DataTableRow>
										</DataTableHeader>
										<DataTableBody>
											{rows.map((row) => (
												<DataTableRow
													key={row.connection_id}
												>
													<DataTableCell className="font-medium">
														{row.server_name}
													</DataTableCell>
													<DataTableCell>
														{renderStatusLabel(row)}
													</DataTableCell>
													<DataTableCell>
														{fallbackLabel(row)}
													</DataTableCell>
													<DataTableCell className="text-right">
														{renderConnectionActions(
															row,
														)}
													</DataTableCell>
												</DataTableRow>
											))}
										</DataTableBody>
									</DataTable>
								</div>
							</>
						) : null}
					</>
				)}
			</CardContent>
		</Card>
	);
}

// Re-export under a default for lazy/dynamic imports if ever needed.
export default UserMCPConnections;

// Trivial loader to keep this file minimal in JSX usage.
export function UserMCPConnectionsLoader() {
	return (
		<div className="flex items-center justify-center py-12">
			<Loader2 className="h-6 w-6 animate-spin text-muted-foreground motion-safe:animate-spin" />
		</div>
	);
}
