import { useState, type MouseEvent } from "react";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export function AgentMcpCopyButton({ agentId }: { agentId: string }) {
	const [pending, setPending] = useState(false);
	const url = `${window.location.origin}/mcp/${agentId}`;
	async function copy(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		if (pending) return;
		setPending(true);
		try {
			await navigator.clipboard.writeText(url);
			toast.success("Agent MCP URL copied");
		} catch {
			toast.error(
				"Could not copy the MCP URL. Check your browser clipboard permissions and try again.",
			);
		} finally {
			setPending(false);
		}
	}
	return (
		<Button
			variant="outline"
			size="sm"
			className="relative z-10 min-h-11"
			onClick={copy}
			disabled={pending}
			title={url}
			aria-label="Copy agent MCP URL"
			data-testid="agent-mcp-copy"
		>
			<Copy className="size-4" aria-hidden="true" />
			{pending ? "Copying…" : "MCP URL"}
		</Button>
	);
}
