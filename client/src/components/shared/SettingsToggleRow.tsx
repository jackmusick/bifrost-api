import { Loader2 } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export function SettingsToggleRow({
	id,
	label,
	description,
	checked,
	disabled,
	busy,
	onChange,
}: {
	id: string;
	label: string;
	description: string;
	checked: boolean;
	disabled: boolean;
	busy?: "loading" | "saving" | undefined;
	onChange: (value: boolean) => void;
}) {
	return (
		<div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
			<div className="min-w-0 space-y-1">
				<Label htmlFor={id}>{label}</Label>
				<p
					id={`${id}-description`}
					className="text-sm text-muted-foreground"
				>
					{description}
				</p>
			</div>
			<div className="flex min-h-11 shrink-0 items-center gap-3">
				<Switch
					id={id}
					checked={checked}
					disabled={disabled}
					onCheckedChange={onChange}
					aria-describedby={`${id}-description`}
				/>
				{busy && (
					<span
						role="status"
						className="flex items-center gap-2 text-xs text-muted-foreground"
					>
						<Loader2
							aria-hidden="true"
							className="size-4 animate-spin motion-reduce:animate-none"
						/>
						{busy === "loading" ? "Loading…" : "Saving…"}
					</span>
				)}
			</div>
		</div>
	);
}
