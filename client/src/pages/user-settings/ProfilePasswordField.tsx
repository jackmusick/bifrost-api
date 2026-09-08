import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ProfilePasswordField({
	id,
	label,
	value,
	onChange,
	autoComplete,
	disabled,
	hint,
}: {
	id: string;
	label: string;
	value: string;
	onChange: (value: string) => void;
	autoComplete: "current-password" | "new-password";
	disabled: boolean;
	hint?: string;
}) {
	const [visible, setVisible] = useState(false);
	return (
		<div className="space-y-2">
			<Label htmlFor={id}>{label}</Label>
			<div className="relative">
				<Input
					id={id}
					type={visible ? "text" : "password"}
					value={value}
					onChange={(e) => onChange(e.target.value)}
					autoComplete={autoComplete}
					disabled={disabled}
					className="min-h-11 pr-12"
					aria-describedby={hint ? `${id}-hint` : undefined}
				/>
				<Button
					type="button"
					variant="ghost"
					size="icon-lg"
					className="absolute right-0 top-0"
					aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`}
					aria-pressed={visible}
					onClick={() => setVisible((v) => !v)}
				>
					<EyeIcon visible={visible} />
				</Button>
			</div>
			{hint && (
				<p id={`${id}-hint`} className="text-xs text-muted-foreground">
					{hint}
				</p>
			)}
		</div>
	);
}
function EyeIcon({ visible }: { visible: boolean }) {
	const Icon = visible ? EyeOff : Eye;
	return <Icon aria-hidden="true" className="size-4 text-muted-foreground" />;
}
