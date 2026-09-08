import { NewConnectionDialog } from "./mcp/components/NewConnectionDialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ServerSettingsSummary } from "./mcp/components/ServerSettingsSummary";
import { ServerConnectionList } from "./mcp/components/ServerConnectionList";
/**
 * MCPServerDetail — server detail with Connections / Server settings / Manifest
 * tabs (mockup §4).
 *
 * Connections tab is the default — that's where 99% of admin work happens.
 * Server settings summarize the template; Manifest explains sync support.
 */

import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, RefreshCw, Trash2 } from "lucide-react";

import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { $api } from "@/lib/api-client";
import { useOrganizations } from "@/hooks/useOrganizations";
import { toast } from "sonner";

export function MCPServerDetail() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	const {
		data: server,
		isLoading,
		error,
		isFetching,
		refetch,
	} = $api.useQuery(
		"get",
		"/api/mcp-servers/{server_id}",
		{ params: { path: { server_id: id! } } },
		{ enabled: !!id },
	);

	const { data: organizations = [] } = useOrganizations();
	const orgById = useMemo(() => {
		const map = new Map<string, string>();
		for (const o of organizations) map.set(o.id, o.name);
		return map;
	}, [organizations]);

	const [createOpen, setCreateOpen] = useState(false);
	const [deleteOpen, setDeleteOpen] = useState(false);

	const deleteServer = $api.useMutation(
		"delete",
		"/api/mcp-servers/{server_id}",
	);

	const handleDelete = async () => {
		if (!id || deleteServer.isPending) return;
		try {
			await deleteServer.mutateAsync({
				params: { path: { server_id: id }, query: { hard: true } },
			});
			setDeleteOpen(false);
			toast.success("MCP server deleted");
			queryClient.invalidateQueries({
				queryKey: ["get", "/api/mcp-servers"],
			});
			navigate("/mcp-servers");
		} catch (err) {
			toast.error(
				err instanceof Error ? err.message : "Failed to delete server",
			);
		}
	};

	if (isLoading) {
		return (
			<div
				role="status"
				aria-label="Loading MCP server"
				className="space-y-4 max-w-7xl mx-auto"
			>
				<Skeleton className="h-10 w-1/3" />
				<Skeleton className="h-32 w-full" />
			</div>
		);
	}

	if (error && !server)
		return (
			<Alert variant="destructive" className="mx-auto max-w-3xl">
				<AlertDescription>
					Server details could not be loaded. Retry to check access
					and availability.
				</AlertDescription>
				<Button
					type="button"
					variant="outline"
					className="min-h-11 mt-3 w-fit"
					disabled={isFetching}
					onClick={() => {
						void refetch();
					}}
				>
					{isFetching ? "Retrying…" : "Retry server"}
				</Button>
			</Alert>
		);

	if (!server) {
		return (
			<Card className="max-w-3xl mx-auto">
				<CardContent className="py-12 text-center">
					<p className="text-muted-foreground">
						MCP server not found.
					</p>
					<Button
						variant="outline"
						className="mt-4"
						onClick={() => navigate("/mcp-servers")}
					>
						<ArrowLeft className="h-4 w-4 mr-1" />
						Back to MCP Servers
					</Button>
				</CardContent>
			</Card>
		);
	}

	return (
		<div className="space-y-6 max-w-7xl mx-auto">
			{error && (
				<Alert variant="destructive">
					<AlertDescription>
						Server details could not refresh. Showing the last
						available snapshot.
					</AlertDescription>
					<Button
						type="button"
						variant="outline"
						className="min-h-11 mt-3 w-fit"
						disabled={isFetching}
						onClick={() => {
							void refetch();
						}}
					>
						{isFetching ? "Retrying…" : "Retry server"}
					</Button>
				</Alert>
			)}
			{/* Breadcrumb / header */}
			<div className="space-y-2">
				<Link
					to="/mcp-servers"
					className="min-h-11 text-sm text-primary hover:underline inline-flex items-center"
				>
					<ArrowLeft className="h-3.5 w-3.5 mr-1" />
					MCP Servers
				</Link>
				<div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
					<div>
						<h1 className="font-display text-2xl font-semibold tracking-tight [overflow-wrap:anywhere] sm:text-3xl">
							{server.name}
						</h1>
						<div className="mt-1 flex min-w-0 flex-wrap items-center gap-2">
							<code className="text-xs text-muted-foreground break-all">
								{server.server_url}
							</code>
							{server.is_active ? (
								<Badge
									variant="default"
									className="bg-[var(--bf-success)]/10 text-[var(--bf-success)]"
								>
									Active
								</Badge>
							) : (
								<Badge variant="secondary">Inactive</Badge>
							)}
						</div>
					</div>
					<Button
						variant="outline"
						size="sm"
						className="min-h-11 text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
						onClick={() => {
							deleteServer.reset();
							setDeleteOpen(true);
						}}
					>
						<Trash2 className="h-4 w-4 mr-1" />
						Delete server
					</Button>
				</div>
			</div>

			<Tabs defaultValue="connections" className="w-full">
				<TabsList
					aria-label="Server views"
					className="grid w-full grid-cols-3 group-data-horizontal/tabs:h-auto sm:w-fit"
				>
					<TabsTrigger
						className="h-auto min-h-11 whitespace-normal"
						value="connections"
					>
						Connections
					</TabsTrigger>
					<TabsTrigger
						className="h-auto min-h-11 whitespace-normal"
						value="settings"
					>
						Server settings
					</TabsTrigger>
					<TabsTrigger
						className="h-auto min-h-11 whitespace-normal"
						value="manifest"
					>
						Manifest
					</TabsTrigger>
				</TabsList>

				<TabsContent value="connections" className="space-y-4 pt-4">
					<div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
						<p className="text-sm text-muted-foreground">
							Per-org connections to this server. Each org sets
							its own OAuth app credentials.
						</p>
						<div className="flex flex-wrap gap-2 [&_button]:min-h-11">
							<Button
								variant="outline"
								size="sm"
								type="button"
								disabled={isFetching}
								onClick={() => {
									queryClient.invalidateQueries({
										queryKey: [
											"get",
											"/api/mcp-servers/{server_id}",
										],
									});
								}}
							>
								<RefreshCw className="h-4 w-4 mr-1" />
								Refresh
							</Button>
							<Button
								size="sm"
								onClick={() => setCreateOpen(true)}
							>
								<Plus className="h-4 w-4 mr-1" />
								New Connection
							</Button>
						</div>
					</div>

					{server.connections && server.connections.length > 0 ? (
						<ServerConnectionList
							serverId={server.id}
							connections={server.connections}
							organizationNames={orgById}
						/>
					) : (
						<Card>
							<CardContent className="py-8 text-center text-sm text-muted-foreground">
								No connections yet. Click "New Connection" to
								add one.
							</CardContent>
						</Card>
					)}
				</TabsContent>

				<TabsContent value="settings" className="pt-4">
					<ServerSettingsSummary server={server} />
				</TabsContent>

				<TabsContent value="manifest" className="pt-4">
					<Card>
						<CardContent className="py-6">
							<p className="text-sm text-muted-foreground">
								Manifest export/import for this server template
								is round-tripped through{" "}
								<code className="text-xs">
									.bifrost/mcp-servers.yaml
								</code>{" "}
								during a global manifest sync. Per-server export
								here is a future enhancement.
							</p>
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>

			<NewConnectionDialog
				open={createOpen}
				onOpenChange={setCreateOpen}
				serverId={server.id}
			/>

			<AlertDialog
				open={deleteOpen}
				onOpenChange={(open) => {
					if (!deleteServer.isPending) setDeleteOpen(open);
				}}
			>
				<AlertDialogContent className="flex max-h-[90dvh] flex-col overflow-hidden">
					<AlertDialogHeader className="min-h-0 overflow-y-auto">
						<AlertDialogTitle>
							Delete this MCP server?
						</AlertDialogTitle>
						<AlertDialogDescription className="[overflow-wrap:anywhere]">
							This will permanently remove the server template{" "}
							<strong>{server.name}</strong> and cascade-delete
							all connections, cached tool catalogs, and per-user
							credentials linked to it. Agents using these tools
							will lose access immediately. This cannot be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					{deleteServer.isError && (
						<p role="alert" className="text-sm text-destructive">
							The server could not be deleted. Try again.
						</p>
					)}
					<AlertDialogFooter className="shrink-0">
						<AlertDialogCancel
							className="min-h-11 lg:min-h-11"
							disabled={deleteServer.isPending}
						>
							Cancel
						</AlertDialogCancel>
						<AlertDialogAction
							onClick={(event) => {
								event.preventDefault();
								void handleDelete();
							}}
							disabled={deleteServer.isPending}
							variant="destructive"
							className="min-h-11 lg:min-h-11"
						>
							{deleteServer.isPending
								? "Deleting..."
								: deleteServer.isError
									? "Retry deletion"
									: "Delete server"}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
