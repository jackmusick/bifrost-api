/**
 * ChatSystemEvent Component
 *
 * Renders inline system events in the chat flow like:
 * - Agent switches (routing, @mentions)
 * - Errors
 * - Status updates
 *
 * These appear as subtle, centered cards that maintain conversation context.
 */

import { Bot, AlertCircle, ArrowRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export type SystemEventType = "agent_switch" | "error" | "info";

export interface SystemEvent {
	id: string;
	type: SystemEventType;
	timestamp: string;
	/** Client message ID for the user turn that caused this event. */
	turnId?: string;
	// For agent switches
	agentName?: string;
	agentId?: string;
	reason?: "routed" | "@mention";
	// For errors
	error?: string;
	// For general info
	message?: string;
}

interface ChatSystemEventProps {
	event: SystemEvent;
}

export function ChatSystemEvent({ event }: ChatSystemEventProps) {
	if (event.type === "agent_switch") {
		return <AgentSwitchEvent event={event} />;
	}

	if (event.type === "error") {
		return <ErrorEvent event={event} />;
	}

	return <InfoEvent event={event} />;
}

function AgentSwitchEvent({ event }: { event: SystemEvent }) {
	const isRouted = event.reason === "routed";

	return (
		<div className="flex justify-center px-3 py-3 sm:px-4">
			<div
				className={cn(
					"inline-flex min-h-11 max-w-full flex-wrap items-center gap-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/30 px-3 py-2 text-sm leading-5 text-foreground",
				)}
			>
				{isRouted ? (
					<>
						<Sparkles className="h-3.5 w-3.5 shrink-0 text-[var(--bf-info)]" />
						<span className="text-muted-foreground">Routed to</span>
					</>
				) : (
					<>
						<ArrowRight className="h-3.5 w-3.5 shrink-0 text-[var(--bf-info)]" />
						<span className="text-muted-foreground">Switched to</span>
					</>
				)}
				<span className="flex min-w-0 basis-full items-start gap-1.5 font-medium [overflow-wrap:anywhere] sm:basis-auto">
					<Bot className="h-3.5 w-3.5 shrink-0 text-[var(--bf-info)]" />
					<span className="min-w-0">{event.agentName}</span>
				</span>
			</div>
		</div>
	);
}

function ErrorEvent({ event }: { event: SystemEvent }) {
	return (
		<div className="flex justify-center px-3 py-3 sm:px-4">
			<div
				className={cn(
					"inline-flex min-h-11 max-w-full items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 px-3 py-2 text-sm leading-5 text-[var(--bf-danger)]",
				)}
			>
				<AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
				<span className="min-w-0 [overflow-wrap:anywhere]">
					{event.error || "An error occurred"}
				</span>
			</div>
		</div>
	);
}

function InfoEvent({ event }: { event: SystemEvent }) {
	return (
		<div className="flex justify-center px-3 py-2 sm:px-4">
			<div className="max-w-full rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 px-3 py-2 text-xs leading-5 text-muted-foreground [overflow-wrap:anywhere]">
				{event.message}
			</div>
		</div>
	);
}
