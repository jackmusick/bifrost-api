import { Link } from "react-router-dom";
import { ArrowRight, Clock3, MessageSquare } from "lucide-react";
import type { components } from "@/lib/v1";
import type { HomeResource } from "@/services/home";

export function RecentWork({
	recent,
	conversations,
	showConversations,
	onOpen,
	busy,
}: {
	recent: HomeResource[];
	conversations?: components["schemas"]["ConversationSummary"][];
	showConversations: boolean;
	onOpen: (resource: HomeResource) => void;
	busy: boolean;
}) {
	return (
		<>
			{(recent.length > 0 ||
				(showConversations && (conversations?.length ?? 0) > 0)) && (
				<section className="space-y-3">
					<div className="flex items-center justify-between">
						<h2 className="text-base font-semibold">
							Continue where you left off
						</h2>
						<Link
							to="/history"
							className="text-sm text-primary hover:underline"
						>
							View history
						</Link>
					</div>
					<div className="grid gap-3 sm:grid-cols-2">
						{showConversations &&
							conversations?.slice(0, 1).map((conversation) => (
								<Link
									key={conversation.id}
									to={`/chat/${conversation.id}`}
									className="flex min-w-0 items-center gap-3 rounded border bg-card p-4 hover:bg-muted/50"
								>
									<MessageSquare className="size-5 shrink-0 text-primary" />
									<span className="min-w-0 flex-1">
										<span className="block truncate text-sm font-medium">
											{conversation.title ||
												"Untitled conversation"}
										</span>
										<span className="mt-1 block truncate text-xs text-muted-foreground">
											{conversation.agent_name || "Chat"}{" "}
											· Resume conversation
										</span>
									</span>
									<ArrowRight className="size-4 shrink-0" />
								</Link>
							))}
						{recent
							.slice(
								0,
								showConversations && conversations?.length
									? 1
									: 2,
							)
							.map((resource) => (
								<button
									key={resource.key}
									disabled={busy}
									onClick={() => onOpen(resource)}
									className="flex min-w-0 items-center gap-3 rounded border bg-card p-4 text-left hover:bg-muted/50"
								>
									<Clock3 className="size-5 shrink-0 text-primary" />
									<span className="min-w-0 flex-1">
										<span className="block truncate text-sm font-medium">
											{resource.name}
										</span>
										<span className="mt-1 block text-xs text-muted-foreground">
											{resource.organization_name} ·
											Recently opened
										</span>
									</span>
									<ArrowRight className="size-4 shrink-0" />
								</button>
							))}
					</div>
				</section>
			)}
		</>
	);
}
