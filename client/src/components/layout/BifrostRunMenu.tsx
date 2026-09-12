import { useId, useRef, useState } from "react";
import { Bot, Copy, Download, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { copyToClipboard } from "@/lib/clipboard";
import { $api } from "@/lib/api-client";
import { downloadBifrostRunPlugin } from "@/services/bifrostRun";

export function BifrostRunMenu() {
	const titleId = useId();
	const downloadPending = useRef(false);
	const copyPending = useRef(false);
	const [isCopying, setIsCopying] = useState(false);
	const [isDownloading, setIsDownloading] = useState(false);
	const [feedback, setFeedback] = useState<{
		error: boolean;
		text: string;
	} | null>(null);
	const copyText = async (value: string, successMessage: string) => {
		if (copyPending.current) return;
		copyPending.current = true;
		setIsCopying(true);
		setFeedback(null);
		try {
			const copied = await copyToClipboard(value);
			setFeedback(
				copied
					? { error: false, text: successMessage }
					: {
							error: true,
							text: "Could not copy to the clipboard. Try again.",
						},
			);
		} catch {
			setFeedback({
				error: true,
				text: "Could not copy to the clipboard. Try again.",
			});
		} finally {
			copyPending.current = false;
			setIsCopying(false);
		}
	};

	const { data: info } = $api.useQuery("get", "/api/mcp/run", undefined, {
		refetchInterval: 60_000,
	});

	if (!info?.enabled) return null;

	const handleDownload = async () => {
		if (downloadPending.current) return;
		downloadPending.current = true;
		setIsDownloading(true);
		setFeedback(null);
		try {
			const { blob, filename } = await downloadBifrostRunPlugin();
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = filename;
			link.click();
			URL.revokeObjectURL(url);
			toast.success("Bifrost Agent downloaded");
		} catch {
			setFeedback({
				error: true,
				text: "Could not download Bifrost Agent. Try again.",
			});
		} finally {
			downloadPending.current = false;
			setIsDownloading(false);
		}
	};

	return (
		<div className="mr-1 sm:mr-2">
			<Popover>
				<PopoverTrigger asChild>
					<Button
						variant="ghost"
						size="icon"
						className="size-11"
						type="button"
						aria-label="Connect AI assistants"
						title="Connect AI assistants"
					>
						<Bot className="h-4 w-4" />
					</Button>
				</PopoverTrigger>
				<PopoverContent
					className="max-h-[var(--radix-popover-content-available-height)] w-[calc(100vw-2rem)] overflow-y-auto gap-0 p-0 sm:w-96"
					collisionPadding={16}
					aria-labelledby={titleId}
					align="end"
					sideOffset={8}
				>
					<div className="border-b p-4">
						<div className="flex items-start gap-3">
							<div className="rounded-[var(--bf-radius-control)] bg-primary/10 p-2 text-primary">
								<Bot className="h-5 w-5" />
							</div>
							<div className="min-w-0">
								<h2 id={titleId} className="font-semibold">
									Use Bifrost with AI
								</h2>
								<p className="mt-1 text-sm text-muted-foreground">
									Connect one AI assistant to all agents and
									tools available in this Bifrost instance.
								</p>
							</div>
						</div>
					</div>

					<div className="space-y-5 p-4">
						{feedback && (
							<p
								role={feedback.error ? "alert" : "status"}
								className={
									feedback.error
										? "sticky top-0 z-10 bg-popover py-2 text-sm text-destructive"
										: "sticky top-0 z-10 bg-popover py-2 text-sm text-muted-foreground"
								}
							>
								{feedback.text}
							</p>
						)}
						<section className="space-y-2">
							<div>
								<p className="text-sm font-medium">
									Agent Plugin
								</p>
								<p className="text-sm leading-6 text-muted-foreground">
									For Claude Code, Codex, GitHub Copilot,
									Cursor, Gemini CLI, and compatible clients.
								</p>
							</div>
							<Button
								className="min-h-11 w-full whitespace-normal"
								type="button"
								disabled={isDownloading}
								onClick={() => void handleDownload()}
							>
								{isDownloading ? (
									<Loader2 className="size-4 motion-safe:animate-spin" />
								) : (
									<Download className="size-4" />
								)}
								{isDownloading
									? "Downloading…"
									: "Download Agent Plugin"}
							</Button>
						</section>

						<div className="border-t" />

						<section className="space-y-4">
							<div>
								<h3 className="text-base font-semibold">
									Manual Setup
								</h3>
								<p className="text-sm leading-6 text-muted-foreground">
									For Claude Desktop, Microsoft Copilot
									Studio, and clients that cannot import the
									plugin.
								</p>
							</div>
							<div className="space-y-2">
								<div className="text-sm font-medium">
									1. Connect the MCP server
								</div>
								<p className="text-sm leading-6 text-muted-foreground">
									Add this as a Streamable HTTP MCP server.
									Setup varies by provider.
								</p>
								<div className="flex flex-col items-start gap-2 rounded-[var(--bf-radius-surface)] border bg-muted/40 p-3">
									<code className="min-w-0 w-full font-mono [overflow-wrap:anywhere] text-sm">
										{info.mcp_url}
									</code>
										<Button
											variant="ghost"
											size="icon"
											className="size-11 shrink-0 self-end"
											type="button"
											aria-label="Copy MCP URL"
											title="Copy MCP URL"
											disabled={isCopying}
											onClick={() =>
												void copyText(
													info.mcp_url,
													"MCP URL copied",
											)
										}
									>
										<Copy className="h-4 w-4" />
									</Button>
								</div>
							</div>
							<div className="space-y-2">
								<p className="text-sm font-medium">
									2. Add the Bifrost behavior
								</p>
								<p className="text-sm leading-6 text-muted-foreground">
									Paste this prompt into your AI service to
									create a reusable skill or agent.
								</p>
								<Button
									variant="outline"
									size="sm"
									className="min-h-11 w-full"
									type="button"
									disabled={isCopying}
									onClick={() =>
										void copyText(
											info.setup_prompt,
											"Setup prompt copied",
										)
									}
								>
									<Copy className="mr-2 h-4 w-4" />
									Copy setup prompt
								</Button>
							</div>
						</section>
					</div>
				</PopoverContent>
			</Popover>
		</div>
	);
}
