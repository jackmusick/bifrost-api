/**
 * Match Suggestion Badge Component
 * Displays a match suggestion with confidence score and accept/reject actions
 */

import { Check, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { MatchSuggestion } from "@/lib/matching";
import { cn } from "@/lib/utils";

interface MatchSuggestionBadgeProps {
	suggestion: MatchSuggestion;
	onAccept: () => void;
	onReject: () => void;
	disabled?: boolean;
}

export function MatchSuggestionBadge({
	suggestion,
	onAccept,
	onReject,
	disabled = false,
}: MatchSuggestionBadgeProps) {
	const isHighConfidence = suggestion.score >= 80;
	const badgeColor = isHighConfidence
		? "bg-[var(--bf-success-soft)] text-[var(--bf-success)] border-[var(--bf-success)]/20"
		: "bg-[var(--bf-warning-soft)] text-[var(--bf-warning)] border-[var(--bf-warning)]/20";

	return (
		<div className="flex min-w-0 flex-wrap items-center gap-2">
			<Badge
				variant="outline"
				className={cn(
					"h-auto max-w-full flex flex-wrap items-center justify-start gap-1.5 px-2.5 py-2 text-sm whitespace-normal [overflow-wrap:anywhere]",
					badgeColor,
				)}
			>
				<span className="font-medium">{suggestion.entityName}</span>
				<span className="text-xs opacity-75">
					({suggestion.score}%)
				</span>
			</Badge>

			<div className="flex items-center gap-1">
				<Button
					size="sm"
					variant="ghost"
					className="min-h-11 text-primary"
					onClick={onAccept}
					disabled={disabled}
					aria-label="Accept suggestion"
				>
					<Check className="h-4 w-4" /> Accept
				</Button>
				<Button
					size="sm"
					variant="ghost"
					className="min-h-11"
					onClick={onReject}
					disabled={disabled}
					aria-label="Reject suggestion"
				>
					<X className="h-4 w-4" /> Reject
				</Button>
			</div>
		</div>
	);
}
