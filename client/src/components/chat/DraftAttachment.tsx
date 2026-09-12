import { FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DraftAttachment({ file, previewUrl, disabled, onRemove }: {
	file: File;
	previewUrl?: string | null;
	disabled: boolean;
	onRemove: () => void;
}) {
	return <div className="flex min-w-0 items-center gap-2 rounded-[var(--bf-radius-control)] border bg-muted/40 p-2">
		{previewUrl ? <img src={previewUrl} alt="" className="size-10 shrink-0 rounded-[var(--bf-radius-control)] object-cover" /> : <FileText className="size-5 shrink-0 text-muted-foreground" />}
		<span className="min-w-0 flex-1 text-xs font-medium [overflow-wrap:anywhere]">{file.name}</span>
		<Button type="button" variant="ghost" size="icon-sm" className="size-11 shrink-0" disabled={disabled} aria-label={`Remove ${file.name}`} onClick={onRemove}><X className="size-4" /></Button>
	</div>;
}
