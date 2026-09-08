import { Check, Copy, ExternalLink, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function FormPrivateLinkPanel({ url, copied, onCopy }: { url: string; copied: boolean; onCopy: () => void }) {
	return (
		<section aria-label="Private form sharing" className="min-w-0 space-y-4">
			<div className="flex items-start gap-3">
				<ShieldCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
				<div className="min-w-0 space-y-1">
					<h3 className="font-medium">Private link</h3>
					<p className="text-sm leading-6 text-muted-foreground">Recipients must sign in and already have access to this form.</p>
				</div>
			</div>
			<Input aria-label="Private form link" readOnly value={url} className="min-h-11 w-full" onFocus={event => event.currentTarget.select()} />
			<div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
				<Button type="button" variant="outline" className="min-h-11 min-w-0 px-2" onClick={onCopy} aria-label="Copy private link">{copied ? <Check aria-hidden="true" className="size-4" /> : <Copy aria-hidden="true" className="size-4" />}{copied ? "Copied" : "Copy link"}</Button>
				<Button variant="outline" className="min-h-11 min-w-0 px-2" asChild><a href={url} target="_blank" rel="noreferrer" aria-label="Open private link"><ExternalLink aria-hidden="true" className="size-4" />Open link</a></Button>
			</div>
			{copied && <p role="status" className="sr-only">Private link copied</p>}
		</section>
	);
}
