import { useId } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";

interface Option {
	label: string;
	value: string;
}
interface OptionsEditorProps {
	options: Option[];
	onChange: (options: Option[]) => void;
	label?: string;
	helpText?: string;
}

function OptionRow({
	option,
	index,
	onUpdate,
	onRemove,
}: {
	option: Option;
	index: number;
	onUpdate: (change: Partial<Option>) => void;
	onRemove: () => void;
}) {
	const id = useId();
	return (
		<div className="min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border p-3">
			<div className="flex items-center justify-between gap-3">
				<span className="text-sm font-medium">Option {index + 1}</span>
				<Button
					type="button"
					variant="ghost"
					size="icon"
					className="h-11 w-11 shrink-0"
					aria-label={`Remove option ${index + 1}`}
					onClick={onRemove}
				>
					<Trash2 className="h-4 w-4" />
				</Button>
			</div>
			<div className="grid min-w-0 gap-3 @min-[28rem]:grid-cols-2">
				<div className="min-w-0 space-y-2">
					<Label htmlFor={`${id}-label`}>
						Label{" "}
						<span className="sr-only">for option {index + 1}</span>
					</Label>
					<Input
						id={`${id}-label`}
						aria-label={`Option ${index + 1} label`}
						placeholder="Label (shown to user)"
						value={option.label}
						onChange={(e) => onUpdate({ label: e.target.value })}
						className="min-h-11"
					/>
				</div>
				<div className="min-w-0 space-y-2">
					<Label htmlFor={`${id}-value`}>
						Stored value{" "}
						<span className="sr-only">for option {index + 1}</span>
					</Label>
					<Input
						id={`${id}-value`}
						aria-label={`Option ${index + 1} value`}
						placeholder="Value (stored)"
						value={option.value}
						onChange={(e) => onUpdate({ value: e.target.value })}
						className="min-h-11 font-mono"
					/>
				</div>
			</div>
		</div>
	);
}

export function OptionsEditor({
	options,
	onChange,
	label = "Options",
	helpText,
}: OptionsEditorProps) {
	const id = useId();
	return (
		<fieldset
			className="@container min-w-0 space-y-3"
			aria-describedby={helpText ? `${id}-help` : undefined}
		>
			<legend className="text-sm font-medium [overflow-wrap:anywhere]">
				{label}
			</legend>
			{helpText && (
				<p
					id={`${id}-help`}
					className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]"
				>
					{helpText}
				</p>
			)}
			{options.map((option, index) => (
				<OptionRow
					key={index}
					option={option}
					index={index}
					onUpdate={(change) =>
						onChange(
							options.map((item, i) =>
								i === index ? { ...item, ...change } : item,
							),
						)
					}
					onRemove={() =>
						onChange(options.filter((_, i) => i !== index))
					}
				/>
			))}
			<Button
				type="button"
				variant="outline"
				onClick={() => onChange([...options, { label: "", value: "" }])}
				className="min-h-11 w-full"
			>
				<Plus className="h-4 w-4" />
				Add Option
			</Button>
		</fieldset>
	);
}
