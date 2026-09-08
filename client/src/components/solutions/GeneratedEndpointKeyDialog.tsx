import { useId, useRef, useState } from "react";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function GeneratedEndpointKeyDialog({ workflowName, rawKey, onClose }: {
	workflowName: string;
	rawKey: string;
	onClose: () => void;
}) {
	const keyId = useId();
	const copyingRef = useRef(false);
	const [copyState, setCopyState] = useState<"idle" | "pending" | "copied" | "failed">("idle");
	const copy = async () => {
		if (copyingRef.current) return;
		copyingRef.current = true;
		setCopyState("pending");
		try {
			await navigator.clipboard.writeText(rawKey);
			setCopyState("copied");
		} catch {
			setCopyState("failed");
		} finally {
			copyingRef.current = false;
		}
	};
	return (
		<Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
			<DialogContent className="max-h-[90dvh] grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0">
				<DialogHeader className="shrink-0 border-b p-5 pr-16! text-left">
					<DialogTitle className="flex items-start gap-2"><KeyRound aria-hidden="true" className="mt-0.5 size-4 shrink-0" />Endpoint key generated</DialogTitle>
					<DialogDescription>Copy this key now. It will not be shown again.</DialogDescription>
				</DialogHeader>
				<div className="min-h-0 space-y-3 overflow-y-auto p-5">
					<Label htmlFor={keyId} className="[overflow-wrap:anywhere]">{workflowName}</Label>
					<Input id={keyId} readOnly value={rawKey} className="min-h-11 font-mono" onFocus={(event) => event.currentTarget.select()} />
					{copyState === "failed" && <p role="alert" className="text-sm text-destructive">Couldn't copy the key. Retry, or select the key and copy it manually.</p>}
					{copyState === "copied" && <p role="status" className="text-sm text-muted-foreground">Endpoint key copied.</p>}
					{copyState === "pending" && <p role="status" className="sr-only">Copying endpoint key…</p>}
				</div>
				<DialogFooter className="shrink-0 flex-col border-t p-5 sm:flex-row">
					<Button variant="outline" className="min-h-11" disabled={copyState === "pending"} onClick={() => void copy()}>{copyState === "pending" ? "Copying…" : copyState === "failed" ? "Retry copy" : copyState === "copied" ? "Copy again" : "Copy"}</Button>
					<Button className="min-h-11" onClick={onClose}>Done</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
