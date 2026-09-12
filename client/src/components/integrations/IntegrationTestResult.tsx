import type { IntegrationTestResponse } from "@/services/integrations";

export function IntegrationTestResult({
	result,
}: {
	result: IntegrationTestResponse;
}) {
	return (
		<div
			role={result.success ? "status" : "alert"}
			className={`min-w-0 space-y-2 rounded-[var(--bf-radius-control)] border p-4 text-sm [overflow-wrap:anywhere] ${result.success ? "border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]" : "border-destructive/20 bg-destructive/10 text-destructive"}`}
		>
			<p className="font-medium">
				{result.success
					? "Connection successful"
					: "Connection test failed"}
			</p>
			<p>{result.message}</p>
			{result.method_called && (
				<p className="text-muted-foreground">
					Method: <code>{result.method_called}()</code>
				</p>
			)}
			{result.duration_ms != null && (
				<p className="text-muted-foreground">
					Duration: {result.duration_ms} ms
				</p>
			)}
			{result.error_details && (
				<p className="whitespace-pre-wrap">{result.error_details}</p>
			)}
		</div>
	);
}
