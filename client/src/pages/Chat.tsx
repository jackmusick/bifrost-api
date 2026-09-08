/**
 * Chat Page
 *
 * Main chat interface for interacting with AI agents.
 * Supports conversation management and real-time streaming.
 */

import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Bot, Settings } from "lucide-react";
import { ChatLayout } from "@/components/chat";
import { useChatStore } from "@/stores/chatStore";
import { useChatAvailability } from "@/hooks/useChatAvailability";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/PageLoader";

export function Chat() {
	const { conversationId } = useParams<{ conversationId?: string }>();
	const setActiveConversation = useChatStore(
		(state) => state.setActiveConversation,
	);
	const {
		isConfigured,
		isPlatformAdmin,
		isLoading: configLoading,
		error,
		isFetching,
		refetch,
	} = useChatAvailability();

	// Set active conversation from URL param
	useEffect(() => {
		setActiveConversation(conversationId ?? null);
	}, [conversationId, setActiveConversation]);

	// Show loading while checking config
	if (configLoading) {
		return <PageLoader message="Loading chat..." />;
	}

	if (error && !isConfigured) {
		return (
			<ChatSetupState
				failed
				pending={isFetching}
				onRetry={() => void refetch()}
			/>
		);
	}
	if (isPlatformAdmin && isConfigured === false) {
		return <ChatSetupState />;
	}

	// Non-admin and chat might not work - they'll see errors when trying
	// For now, we let them through and errors will be handled by the chat components

	return (
		<div className="h-full min-h-0 min-w-0">
			<ChatLayout initialConversationId={conversationId} />
		</div>
	);
}

export default Chat;

function ChatSetupState({
	failed = false,
	pending = false,
	onRetry,
}: {
	failed?: boolean;
	pending?: boolean;
	onRetry?: () => void;
}) {
	return (
		<div className="flex h-full min-h-0 items-center justify-center overflow-y-auto px-4 py-8 sm:px-6">
			<section
				className="w-full max-w-md space-y-6 text-center [overflow-wrap:anywhere]"
				aria-labelledby="chat-setup-heading"
			>
				<div className="mx-auto flex size-16 items-center justify-center rounded-[var(--bf-radius-surface)] bg-muted">
					<Bot
						className="size-8 text-muted-foreground"
						aria-hidden="true"
					/>
				</div>
				<div className="space-y-3">
					<h1
						id="chat-setup-heading"
						className="font-display text-2xl font-semibold"
					>
						{failed ? "Chat could not load" : "Set up AI chat"}
					</h1>
					<p
						role={failed ? "alert" : undefined}
						className="text-sm leading-relaxed text-muted-foreground"
					>
						{failed
							? "Model availability could not be checked. Try again to open chat."
							: "Add a provider connection and enable a model profile for Chat to get started."}
					</p>
				</div>
				{failed ? (
					<Button
						className="min-h-11 w-full sm:w-auto"
						disabled={pending}
						onClick={onRetry}
					>
						{pending ? "Retrying…" : "Retry chat"}
					</Button>
				) : (
					<Button className="min-h-11 w-full sm:w-auto" asChild>
						<Link to="/settings/ai">
							<Settings className="size-4" />
							Configure AI models
						</Link>
					</Button>
				)}
			</section>
		</div>
	);
}
