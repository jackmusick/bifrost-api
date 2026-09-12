import { Button } from "@/components/ui/button";
import { Copy } from "lucide-react";
import type { components } from "@/lib/v1";
export function GeneratedSDKSummary({
	result,
	onCopy,
	copyMessage,
}: {
	result: components["schemas"]["GenerateSDKResponse"];
	onCopy: () => void;
	copyMessage?: string | null;
}) {
	return (
		<div className="min-w-0 space-y-4">
			<div className="grid min-w-0 grid-cols-2 gap-4 text-sm [overflow-wrap:anywhere] [&>div:nth-child(-n+2)]:col-span-2">
				<div>
					<span className="text-muted-foreground">Module:</span>
					<p className="font-mono font-medium">
						{result.module_name}
					</p>
				</div>
				<div>
					<span className="text-muted-foreground">Path:</span>
					<p className="font-mono text-xs">{result.module_path}</p>
				</div>
				<div>
					<span className="text-muted-foreground">Endpoints:</span>
					<p className="font-medium">{result.endpoint_count}</p>
				</div>
				<div>
					<span className="text-muted-foreground">Schemas:</span>
					<p className="font-medium">{result.schema_count}</p>
				</div>
			</div>

			<div className="space-y-2">
				<p className="text-sm font-medium">Usage Example</p>
				<div className="min-w-0 space-y-2">
					<pre
						tabIndex={0}
						aria-label="SDK usage example"
						className="max-h-64 overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere] rounded-[var(--bf-radius-control)] bg-muted p-3 text-xs"
					>
						<code>{result.usage_example}</code>
					</pre>
					<Button
						variant="ghost"

						className="min-h-11"
						onClick={onCopy}
					>
						<Copy className="size-4" /> Copy usage example
					</Button>
					{copyMessage && (
						<p
							role="status"
							className="text-sm text-muted-foreground [overflow-wrap:anywhere]"
						>
							{copyMessage}
						</p>
					)}
				</div>
			</div>
		</div>
	);
}
