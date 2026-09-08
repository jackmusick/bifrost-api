import { useId, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export type HmacScheme = "shopify" | "halopsa";
interface HmacSecretCreateFormProps {
	name: string;
	secret: string;
	scheme: HmacScheme;
	busy: boolean;
	creating: boolean;
	error: boolean;
	onName: (value: string) => void;
	onSecret: (value: string) => void;
	onScheme: (value: HmacScheme) => void;
	onSubmit: (event: FormEvent) => void;
	onCancel: () => void;
}

export function HmacSecretCreateForm({ name, secret, scheme, busy, creating, error, onName, onSecret, onScheme, onSubmit, onCancel }: HmacSecretCreateFormProps) {
	const id = useId();
	return (
		<form aria-label="Create embed secret" aria-busy={creating} onSubmit={onSubmit} className="min-w-0 space-y-4 rounded-[var(--bf-radius-surface)] border bg-muted/20 p-[var(--bf-surface-pad)]">
			<div className="space-y-2"><Label htmlFor={`${id}-name`}>Name</Label><Input id={`${id}-name`} required autoFocus disabled={busy} value={name} onChange={event => onName(event.target.value)} placeholder="e.g., Halo Production" className="min-h-11" /></div>
			<div className="space-y-2"><Label htmlFor={`${id}-secret`}>Secret (optional)</Label><Input id={`${id}-secret`} type="password" autoComplete="new-password" disabled={busy} value={secret} onChange={event => onSecret(event.target.value)} aria-describedby={`${id}-secret-help`} className="min-h-11 font-mono" /><p id={`${id}-secret-help`} className="text-sm text-muted-foreground">Leave blank to generate a new secret.</p></div>
			<div className="space-y-2"><Label htmlFor={`${id}-scheme`}>HMAC scheme</Label><Select value={scheme} disabled={busy} onValueChange={value => onScheme(value as HmacScheme)}><SelectTrigger id={`${id}-scheme`} aria-describedby={`${id}-scheme-help`} className="min-h-11 w-full"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="shopify" className="min-h-11">Standard</SelectItem><SelectItem value="halopsa" className="min-h-11">HaloPSA</SelectItem></SelectContent></Select><p id={`${id}-scheme-help`} className="text-sm text-muted-foreground">{scheme === "shopify" ? "Signs all query parameters (recommended for most integrations)." : "Signs only agent_id. Use for HaloPSA Custom Tab embeds."}</p></div>
			{error && <p role="alert" className="text-sm text-destructive">Could not create the secret. Your entries are still here; try again.</p>}
			{creating && <p role="status" className="text-sm text-muted-foreground">Creating embed secret…</p>}
			<div className="flex flex-wrap gap-2"><Button type="button" variant="outline" className="min-h-11" disabled={busy} onClick={onCancel}>Cancel</Button><Button type="submit" className="min-h-11" disabled={busy || !name.trim()}>{creating ? "Creating..." : error ? "Retry creation" : "Add"}</Button></div>
		</form>
	);
}
