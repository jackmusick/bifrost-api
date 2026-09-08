import { AlertCircle, CheckCircle2, Loader2, type LucideIcon } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";

export type MaintenanceOutcome = "complete" | "failed" | "unknown" | "skipped";

export function MaintenanceActionRow({ id, label, description, icon: Icon, checked, disabled, status, onToggle }: {
	id: string;
	label: string;
	description: string;
	icon: LucideIcon;
	checked: boolean;
	disabled: boolean;
	status: "idle" | "queued" | "running" | MaintenanceOutcome;
	onToggle: () => void;
}) {
	return <div className="min-w-0 p-4">
		<label htmlFor={`action-${id}`} className="flex min-h-11 cursor-pointer items-start gap-3">
			<Checkbox id={`action-${id}`} className="mt-0.5" checked={checked} onCheckedChange={onToggle} disabled={disabled} />
			<Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
			<span className="min-w-0"><span className="block text-sm font-medium [overflow-wrap:anywhere]">{label}</span><span className="mt-1 block text-sm text-muted-foreground [overflow-wrap:anywhere]">{description}</span></span>
		</label>
		{status !== "idle" && <p role={status === "failed" || status === "unknown" ? "alert" : "status"} className={`mt-2 flex items-start gap-2 text-sm ${status === "failed" ? "text-destructive" : status === "complete" ? "text-[var(--bf-success)]" : "text-muted-foreground"}`}>
			{status === "running" ? <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin motion-reduce:animate-none" /> : status === "complete" ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" /> : status === "failed" ? <AlertCircle className="mt-0.5 size-4 shrink-0" /> : null}
			{status === "unknown" ? "Status unavailable. Check scheduler logs before running again." : status === "failed" ? "Failed. Run the selected action again to retry." : status === "running" ? "Running…" : status === "queued" ? "Queued" : status === "skipped" ? "Skipped" : "Complete"}
		</p>}
	</div>;
}
