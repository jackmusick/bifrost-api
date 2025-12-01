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

export function OptionsEditor({
	options,
	onChange,
	label = "Options",
	helpText,
}: OptionsEditorProps) {
	const handleAddOption = () => {
		onChange([...options, { label: "", value: "" }]);
	};

	const handleRemoveOption = (index: number) => {
		onChange(options.filter((_, i) => i !== index));
	};

	const handleUpdateLabel = (index: number, newLabel: string) => {
		const newOptions = [...options];
		if (newOptions[index]) {
			newOptions[index].label = newLabel;
			onChange(newOptions);
		}
	};

	const handleUpdateValue = (index: number, newValue: string) => {
		const newOptions = [...options];
		if (newOptions[index]) {
			newOptions[index].value = newValue;
			onChange(newOptions);
		}
	};

	return (
		<div className="space-y-2">
			<Label>{label}</Label>
			<div className="space-y-2">
				{options.map((option, index) => (
					<div key={index} className="flex gap-2">
						<Input
							placeholder="Label (shown to user)"
							value={option.label}
							onChange={(e) =>
								handleUpdateLabel(index, e.target.value)
							}
							className="flex-1"
						/>
						<Input
							placeholder="Value (stored)"
							value={option.value}
							onChange={(e) =>
								handleUpdateValue(index, e.target.value)
							}
							className="flex-1"
						/>
						<Button
							type="button"
							variant="outline"
							size="icon"
							onClick={() => handleRemoveOption(index)}
						>
							<Trash2 className="h-4 w-4" />
						</Button>
					</div>
				))}
				<Button
					type="button"
					variant="outline"
					size="sm"
					onClick={handleAddOption}
					className="w-full"
				>
					<Plus className="h-4 w-4 mr-2" />
					Add Option
				</Button>
			</div>
			{helpText && (
				<p className="text-xs text-muted-foreground">{helpText}</p>
			)}
		</div>
	);
}
