import { useId } from "react";
import { Switch } from "@/components/ui/switch";

interface FormSharingToggleProps {
	title: string;
	label: string;
	description: string;
	checked: boolean;
	disabled: boolean;
	pendingText?: string | undefined;
	onChange: (checked: boolean) => void;
}

export function FormSharingToggle({ title, label, description, checked, disabled, pendingText, onChange }: FormSharingToggleProps) {
	const id = useId();
	return (
		<div className="min-w-0 space-y-2">
			<label htmlFor={id} className={`flex min-h-11 items-center justify-between gap-4 py-2 ${disabled ? "cursor-default" : "cursor-pointer"}`}>
				<span className="min-w-0 text-sm font-medium">{title}{label !== title && <span aria-hidden="true" className="mt-1 block text-xs font-normal text-muted-foreground">{label}</span>}</span>
				<Switch id={id} aria-label={label} aria-describedby={`${id}-description`} checked={checked} disabled={disabled} onCheckedChange={onChange} className="shrink-0" />
			</label>
			<p id={`${id}-description`} className="text-sm text-muted-foreground">{description}</p>
			{pendingText && <p role="status" className="text-sm text-muted-foreground">{pendingText}</p>}
		</div>
	);
}
