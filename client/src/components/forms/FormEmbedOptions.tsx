import { useId } from "react";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

export type EmbedTheme = "light" | "dark" | "system";

interface FormEmbedOptionsProps {
	theme: EmbedTheme;
	headerVisible: boolean;
	transparent: boolean;
	onTheme: (theme: EmbedTheme) => void;
	onHeaderVisible: (visible: boolean) => void;
	onTransparent: (transparent: boolean) => void;
}

export function FormEmbedOptions({ theme, headerVisible, transparent, onTheme, onHeaderVisible, onTransparent }: FormEmbedOptionsProps) {
	const id = useId();
	return (
		<fieldset aria-describedby={`${id}-help`} className="min-w-0 space-y-4 rounded-[var(--bf-radius-surface)] border p-[var(--bf-surface-pad)]">
			<legend className="px-1 text-sm font-medium">Embed Options</legend>
			<div className="space-y-2">
				<Label htmlFor={`${id}-theme`}>Theme</Label>
				<Select value={theme} onValueChange={value => onTheme(value as EmbedTheme)}>
					<SelectTrigger id={`${id}-theme`} className="min-h-11 w-full"><SelectValue /></SelectTrigger>
					<SelectContent>
						<SelectItem value="light" className="min-h-11">Light</SelectItem>
						<SelectItem value="dark" className="min-h-11">Dark</SelectItem>
						<SelectItem value="system" className="min-h-11">System</SelectItem>
					</SelectContent>
				</Select>
			</div>
			<div className="divide-y">
				<label htmlFor={`${id}-header`} className="flex min-h-14 cursor-pointer items-center justify-between gap-4 py-3 text-sm">
					<span className="min-w-0">Show Header<span aria-hidden="true" className="mt-1 block text-xs text-muted-foreground">{headerVisible ? "Shown" : "Hidden"}</span></span>
					<Switch id={`${id}-header`} checked={headerVisible} onCheckedChange={onHeaderVisible} className="shrink-0" />
				</label>
				<label htmlFor={`${id}-transparent`} className="flex min-h-14 cursor-pointer items-center justify-between gap-4 py-3 text-sm">
					<span className="min-w-0">Transparent Background<span aria-hidden="true" className="mt-1 block text-xs text-muted-foreground">{transparent ? "Transparent" : "Solid"}</span></span>
					<Switch id={`${id}-transparent`} checked={transparent} onCheckedChange={onTransparent} className="shrink-0" />
				</label>
			</div>
			<p id={`${id}-help`} className="text-sm text-muted-foreground">These options only change the code you copy.</p>
		</fieldset>
	);
}
