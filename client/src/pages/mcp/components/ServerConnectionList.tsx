import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ConnectionSummary {
	id: string;
	organization_id: string;
	service_oauth_token_id?: string | null;
	available_in_chat: boolean;
	available_to_autonomous: boolean;
	tools?: unknown[] | null;
}

export function ServerConnectionList({
	serverId,
	connections,
	organizationNames,
}: {
	serverId: string;
	connections: ConnectionSummary[];
	organizationNames: Map<string, string>;
}) {
	return (
		<ul
			aria-label="Organization connections"
			className="grid min-w-0 gap-4 lg:grid-cols-2"
		>
			{connections.map((connection) => {
				const name =
					organizationNames.get(connection.organization_id) ??
					connection.organization_id;
				return (
					<li
						key={connection.id}
						className="min-w-0 space-y-4 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]"
					>
						<div className="space-y-2">
							<h3 className="font-semibold [overflow-wrap:anywhere]">
								{name}
							</h3>
							<Badge
								variant="outline"
								className={
									connection.service_oauth_token_id
										? "bg-[var(--bf-success)]/10 text-[var(--bf-success)]"
										: "bg-[var(--bf-warning)]/10 text-[var(--bf-warning)]"
								}
							>
								{connection.service_oauth_token_id
									? "Connected"
									: "No service connection"}
							</Badge>
						</div>
						<dl className="grid grid-cols-2 gap-3 text-sm">
							<div className="col-span-2">
								<dt className="text-xs text-muted-foreground">
									Tools cached
								</dt>
								<dd>{connection.tools?.length ?? 0}</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									User chat
								</dt>
								<dd>
									{connection.available_in_chat
										? "Available"
										: "Unavailable"}
								</dd>
							</div>
							<div>
								<dt className="text-xs text-muted-foreground">
									Autonomous agents
								</dt>
								<dd>
									{connection.available_to_autonomous
										? "Available"
										: "Unavailable"}
								</dd>
							</div>
						</dl>
						<Button
							asChild
							variant="outline"
							className="min-h-11 w-full"
						>
							<Link
								aria-label={`Manage ${name} connection`}
								to={`/mcp-servers/${serverId}/connections/${connection.id}/edit`}
							>
								Manage connection
							</Link>
						</Button>
					</li>
				);
			})}
		</ul>
	);
}
