import { Badge } from "@/components/ui/badge";

interface Props {
	status: string;
}

const LABELS: Record<
	string,
	{
		text: string;
		variant: "default" | "secondary" | "outline" | "destructive";
		className?: string;
	}
> = {
	active: {
		text: "Active",
		variant: "outline",
		className:
			"border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)] text-[var(--bf-success)]",
	},
	pending: {
		text: "Pending invite",
		variant: "outline",
		className:
			"border-[var(--bf-warning)]/20 bg-[var(--bf-warning-soft)] text-[var(--bf-warning)]",
	},
	expired: {
		text: "Invite expired",
		variant: "outline",
		className:
			"border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]",
	},
	never_invited: { text: "Not invited", variant: "outline" },
};

export function UserStatusBadge({ status }: Props) {
	const cfg = LABELS[status] ?? { text: "Unknown status", variant: "outline" as const, className: "text-muted-foreground" };
	return (
		<Badge variant={cfg.variant} className={`text-xs ${cfg.className ?? ""}`}>
			{cfg.text}
		</Badge>
	);
}
