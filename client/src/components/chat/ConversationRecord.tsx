import { MessageSquare, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ConversationSummary } from "@/hooks/useChat";

	// Format relative time
const formatTime = (dateStr: string) => {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return "now";
		if (diffMins < 60) return `${diffMins}m`;
		if (diffHours < 24) return `${diffHours}h`;
		if (diffDays < 7) return `${diffDays}d`;
		return date.toLocaleDateString();
	};

export function ConversationRecord({ conversation: conv, active, onSelect, onDelete }: {
conversation: ConversationSummary;
active: boolean;
onSelect: (conversation: ConversationSummary) => void;
onDelete: (conversation: ConversationSummary) => void;
}) { return (
								<div
									className={cn(
										"group flex items-start rounded-[var(--bf-radius-control)] transition-colors motion-reduce:transition-none hover:bg-accent",
										active &&
											"bg-accent",
									)}
								>
									<button
										type="button"
										aria-current={active ? "page" : undefined}
										aria-label={`Open ${conv.title || conv.agent_name || "Untitled"}`}
										className="flex min-h-11 min-w-0 flex-1 items-start gap-2 rounded-[var(--bf-radius-control)] p-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
										onClick={() => onSelect(conv)}
									>
										<MessageSquare className="h-4 w-4 mt-1 text-muted-foreground shrink-0" />
										<div className="flex-1 min-w-0">
											<div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
												<span className="font-medium text-sm [overflow-wrap:anywhere]">
													{conv.title ||
														conv.agent_name ||
														"Untitled"}
												</span>
												<span className="text-xs text-muted-foreground shrink-0">
													{formatTime(conv.updated_at)}
												</span>
											</div>
											{conv.last_message_preview && (
												<p className="mt-1 text-xs text-muted-foreground line-clamp-2 [overflow-wrap:anywhere]">
													{conv.last_message_preview}
												</p>
											)}
										</div>
									</button>
									<Button
										variant="ghost"
										size="icon-sm"
										className="mt-1 size-11 shrink-0"
										aria-label={`Delete ${conv.title || conv.agent_name || "Untitled"}`}
										onClick={() => onDelete(conv)}
									>
										<Trash2 className="h-3 w-3" />
									</Button>
								</div>
); }
