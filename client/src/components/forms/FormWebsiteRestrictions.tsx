import { useEffect, useId, useRef } from "react";
import { ChevronDown, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface FormWebsiteRestrictionsProps {
	focusRetryRequest?: number;
	open: boolean;
	busy: boolean;
	value: string;
	published: boolean;
	state: "idle" | "saving" | "saved" | "error";
	onOpenChange: (open: boolean) => void;
	onChange: (value: string) => void;
	onRetry: () => void;
}

export function FormWebsiteRestrictions({ focusRetryRequest = 0, open, busy, value, published, state, onOpenChange, onChange, onRetry }: FormWebsiteRestrictionsProps) {
	const id = useId();
	const retryRef = useRef<HTMLButtonElement>(null);
	const focusedRequest = useRef(0);
	useEffect(() => {
		if (open && !busy && state === "error" && focusRetryRequest > focusedRequest.current) {
			retryRef.current?.focus();
			focusedRequest.current = focusRetryRequest;
		}
	}, [open, busy, state, focusRetryRequest]);
	return (
		<Collapsible open={open} onOpenChange={onOpenChange} className="min-w-0 border-t">
			<CollapsibleTrigger className="flex min-h-11 w-full items-center justify-between gap-3 py-3 text-left text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring">
				<span className="flex min-w-0 flex-wrap items-baseline gap-x-2">Website Restrictions<span className="text-xs font-normal text-muted-foreground">Optional</span></span>
				<ChevronDown aria-hidden="true" className={`size-4 shrink-0 transition-transform duration-[var(--bf-motion-disclosure)] motion-reduce:transition-none ${open ? "rotate-180" : ""}`} />
			</CollapsibleTrigger>
			<CollapsibleContent className="space-y-3 pb-[var(--bf-surface-pad)] pt-2">
				<Label htmlFor={`${id}-origins`}>Allowed Website Origins</Label>
				<Textarea id={`${id}-origins`} value={value} onChange={event => onChange(event.target.value)} aria-describedby={`${id}-help${published ? ` ${id}-status` : ""}`} placeholder="https://www.example.com" rows={3} className="field-sizing-fixed min-w-0 max-w-full font-mono text-sm" />
				<p id={`${id}-help`} className="text-sm text-muted-foreground">Limit which websites can frame this form. Use one exact origin per line; leave empty to allow any website.</p>
				{published && <div className="space-y-3">
					<p id={`${id}-status`} role={state === "error" ? "alert" : "status"} className={`text-sm ${state === "error" ? "text-destructive" : "text-muted-foreground"}`}>
						{state === "saving" ? "Saving restrictions…" : state === "saved" ? "Restrictions saved" : state === "error" ? "Restrictions could not be saved. Check each origin and try again." : "Changes save automatically."}
					</p>
					{state === "error" && <Button ref={retryRef} type="button" variant="outline" className="min-h-11" disabled={busy} onClick={onRetry}><RefreshCw aria-hidden="true" className="size-4" />Retry saving</Button>}
				</div>}
			</CollapsibleContent>
		</Collapsible>
	);
}
