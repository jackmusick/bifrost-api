/**
 * ChatSidebar Component
 *
 * Left sidebar showing:
 * - List of available agents
 * - Recent conversations
 * - New conversation button
 */

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Files, Plus, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConversationRecord } from "./ConversationRecord";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useConversations, useDeleteConversation } from "@/hooks/useChat";
import type { ConversationSummary } from "@/hooks/useChat";

interface ChatSidebarProps {
	className?: string;
	onClose?: () => void;
	onConversationSelected?: () => void;
}

export function ChatSidebar({
	className,
	onClose,
	onConversationSelected,
}: ChatSidebarProps) {
	const navigate = useNavigate();
	const location = useLocation();
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const [searchTerm, setSearchTerm] = useState("");
	const [deleteTarget, setDeleteTarget] =
		useState<ConversationSummary | null>(null);

	// Store state
	const { activeConversationId, setActiveConversation, setActiveAgent } =
		useChatStore();

	// API hooks
	const { data: conversations, isLoading: isLoadingConversations, isError: conversationsError, isFetching: fetchingConversations, refetch: refetchConversations } =
		useConversations();
	const deleteConversation = useDeleteConversation();

	// Filter conversations by search term
	const filteredConversations = conversations?.filter((conv) => {
		const term = searchTerm.trim().toLowerCase();
		if (!term) return true;
		return (
			conv.title?.toLowerCase().includes(term) ||
			conv.agent_name?.toLowerCase().includes(term) ||
			conv.last_message_preview?.toLowerCase().includes(term)
		);
	});

	// Handle starting new conversation
	const handleNewChat = () => {
		setActiveConversation(null);
		setActiveAgent(null);
		navigate("/chat");
		onConversationSelected?.();
	};

	// Handle selecting existing conversation
	const handleSelectConversation = (conv: ConversationSummary) => {
		setActiveConversation(conv.id);
		setActiveAgent(conv.agent_id ?? null);
		// Update URL to enable bookmarking/sharing
		navigate(`/chat/${conv.id}`);
		onConversationSelected?.();
	};

	// Handle delete confirmation
	const handleDeleteConfirm = () => {
		if (!deleteTarget || deleteConversation.isPending) return;
		const wasActive = activeConversationId === deleteTarget.id;
		setDeleteError(null);
		deleteConversation.mutate({
			params: { path: { conversation_id: deleteTarget.id } },
		}, {
			onSuccess: () => {
				setDeleteTarget(null);
				if (wasActive) navigate("/chat");
			},
			onError: () => setDeleteError("Could not delete this conversation. Try again."),
		});
	};


	return (
		<div
			className={cn(
				"flex min-h-0 flex-col h-full bg-background",
				className,
			)}
		>
			{/* Header */}
			<div className="p-4 border-b space-y-2">
				<div className="flex items-center justify-between">
					<h2 className="font-display font-semibold text-lg">Chat</h2>
					{onClose && (
						<Button
							variant="ghost"
							size="icon-sm"
							className="size-11 lg:hidden"
							onClick={onClose}
							aria-label="Close chat sidebar"
						>
							<X className="h-4 w-4" />
						</Button>
					)}
				</div>
				<Button
					variant="ghost"
					className="min-h-11 w-full justify-start gap-2"
					onClick={handleNewChat}
				>
					<Plus className="h-4 w-4" />
					New Chat
				</Button>
				<Button
					variant="ghost"
					className={cn(
						"min-h-11 w-full justify-start gap-2",
						location.pathname === "/chat/artifacts" && "bg-accent",
					)}
					onClick={() => {
						navigate("/chat/artifacts");
						onConversationSelected?.();
					}}
				>
					<Files className="h-4 w-4" />
					Artifacts
				</Button>
				<div className="relative">
					<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
					<Input
						aria-label="Search conversations"
						placeholder="Search conversations..."
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="min-h-11 pl-9"
					/>
				</div>
			</div>

			<div className="flex-1 overflow-y-auto p-4">
				{/* Conversations Section */}
				<div>
					<h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
						Recent Conversations
					</h3>
					{conversationsError && (
						<div role="alert" className="mb-3 space-y-3 rounded-[var(--bf-radius-control)] border border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] p-4 text-sm">
							<p>{conversations ? "Could not refresh conversations. Previously loaded conversations are still shown." : "Conversations could not be loaded."}</p>
							<Button type="button" variant="outline" className="min-h-11" disabled={fetchingConversations} onClick={() => { void refetchConversations(); }}>{fetchingConversations ? "Retrying…" : "Retry conversations"}</Button>
						</div>
					)}
					{isLoadingConversations ? (
						<div role="status" aria-label="Loading conversations" className="space-y-2">
							{[1, 2, 3].map((i) => (
								<Skeleton key={i} className="h-14 w-full" />
							))}
						</div>
					) : conversationsError && !conversations ? null : filteredConversations &&
					  filteredConversations.length > 0 ? (
						<div className="space-y-1">
							{filteredConversations.map((conv) => (
								<ConversationRecord key={conv.id} conversation={conv} active={activeConversationId === conv.id} onSelect={handleSelectConversation} onDelete={(conversation) => { setDeleteError(null); setDeleteTarget(conversation); }} />
							))}
						</div>
					) : (
						<p className="text-sm text-muted-foreground py-2">
							{searchTerm.trim()
								? "No matching conversations"
								: "No conversations yet"}
						</p>
					)}
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<AlertDialog
				open={!!deleteTarget}
				onOpenChange={(open) => !open && !deleteConversation.isPending && setDeleteTarget(null)}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>
							Delete Conversation?
						</AlertDialogTitle>
						<AlertDialogDescription className="[overflow-wrap:anywhere]">
							This will delete the conversation "
							{deleteTarget?.title ||
								deleteTarget?.agent_name ||
								"Untitled"}
							". This action cannot be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					{deleteError && <p role="alert" className="text-sm text-destructive">{deleteError}</p>}
					<AlertDialogFooter>
						<AlertDialogCancel disabled={deleteConversation.isPending}>Cancel</AlertDialogCancel>
						<AlertDialogAction
							disabled={deleteConversation.isPending}
							onClick={(event) => { event.preventDefault(); handleDeleteConfirm(); }}
							className="min-h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							{deleteConversation.isPending ? "Deleting…" : "Delete"}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
