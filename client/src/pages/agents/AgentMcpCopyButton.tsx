import { useState } from "react";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

type CopyEvent = {
	preventDefault: () => void;
	stopPropagation: () => void;
};

export function AgentMcpCopyButton({
	agentId,
	variant = "button",
}: {
	agentId: string;
	variant?: "button" | "menuitem";
}) {
	const [pending, setPending] = useState(false);
	const url = `${window.location.origin}/mcp/${agentId}`;
	async function copy(event: CopyEvent) {
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
	if (variant === "menuitem") {
		return (
			<DropdownMenuItem
				className="min-h-11"
				onSelect={(event) => void copy(event)}
				disabled={pending}
			>
				<Copy className="size-4" aria-hidden="true" />
				{pending ? "Copying…" : "Copy MCP URL"}
			</DropdownMenuItem>
		);
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
		>
			<Copy className="size-4" aria-hidden="true" />
			{pending ? "Copying…" : "MCP URL"}
		</Button>
	);
}
