import { Card, CardContent } from "@/components/ui/card";

interface ServerSettings {
	name: string;
	server_url: string;
	redirect_url?: string | null;
	oauth_provider_id?: string | null;
	discovery_metadata?: unknown;
}

export function ServerSettingsSummary({ server }: { server: ServerSettings }) {
	return (
		<Card>
			<CardContent className="space-y-6 p-[var(--bf-surface-pad)]">
				<dl className="grid min-w-0 gap-5 sm:grid-cols-2">
					{[
						{ label: "Name", value: server.name, mono: false },
						{
							label: "Server URL",
							value: server.server_url,
							mono: true,
						},
						{
							label: "Redirect URL",
							value: server.redirect_url ?? "Not set",
							mono: !!server.redirect_url,
						},
						{
							label: "OAuth provider",
							value:
								server.oauth_provider_id ??
								"None — cannot start service-token flow until linked",
							mono: !!server.oauth_provider_id,
						},
					].map((field) => (
						<div key={field.label} className="min-w-0 space-y-1">
							<dt className="text-xs text-muted-foreground">
								{field.label}
							</dt>
							<dd
								className={`[overflow-wrap:anywhere] ${field.mono ? "font-mono text-xs" : "text-sm"}`}
							>
								{field.value}
							</dd>
						</div>
					))}
				</dl>
				<section
					aria-labelledby="server-discovery-heading"
					className="min-w-0 space-y-3"
				>
					<h3
						id="server-discovery-heading"
						className="text-sm font-semibold"
					>
						Discovery metadata
					</h3>
					<pre
						tabIndex={0}
						aria-label="Discovery metadata JSON"
						className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-[var(--bf-radius-surface)] border bg-muted/40 p-4 font-mono text-xs [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						{JSON.stringify(
							server.discovery_metadata ?? null,
							null,
							2,
						)}
					</pre>
				</section>
			</CardContent>
		</Card>
	);
}
