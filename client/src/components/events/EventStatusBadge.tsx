import { Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { EventStatus } from "@/services/events";

const states = {
	received: {
		label: "Received",
		Icon: Clock,
		color: "text-muted-foreground",
	},
	processing: {
		label: "Processing",
		Icon: Loader2,
		color: "text-[var(--bf-info)]",
	},
	completed: {
		label: "Completed",
		Icon: CheckCircle2,
		color: "text-[var(--bf-success)]",
	},
	failed: {
		label: "Failed",
		Icon: XCircle,
		color: "text-[var(--bf-danger)]",
	},
};

export function EventStatusBadge({ status }: { status: EventStatus }) {
	const state = states[status] ?? {
		label: "Unknown",
		Icon: Clock,
		color: "text-muted-foreground",
	};
	return (
		<Badge
			variant="outline"
			className={`h-auto gap-1.5 py-1 text-sm ${state.color}`}
		>
			<state.Icon
				aria-hidden="true"
				className={`size-4 shrink-0 ${status === "processing" ? "motion-safe:animate-spin" : ""}`}
			/>
			{state.label}
		</Badge>
	);
}
