import { cn } from "@/lib/utils";
export function AuditOutcome({ outcome }: { outcome: string }) {
	return (
		<span
			className={cn(
				"inline-flex rounded-full px-2 py-1 text-xs font-medium capitalize",
				outcome === "failure"
					? "bg-[var(--bf-danger-soft)] text-[var(--bf-danger)]"
					: outcome === "success"
						? "bg-[var(--bf-success-soft)] text-[var(--bf-success)]"
						: "bg-muted text-muted-foreground",
			)}
		>
			{outcome}
		</span>
	);
}
