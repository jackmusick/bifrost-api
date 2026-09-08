/**
 * Data Provider Inputs Configuration Component
 * Supports static, fieldRef, and expression modes for data provider parameters
 * Part of Phase 3-5: User Stories 1-3 - Complete Dynamic Data Provider Inputs
 */

import { useId } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { ExpressionEditor } from "@/components/ui/expression-editor";
import type { components } from "@/lib/v1";
import type {
	DataProviderInputConfig,
	DataProviderInputMode,
} from "@/lib/client-types";

// Data providers are stored in workflows table with type='data_provider'
// They have the same metadata structure (including parameters)
type WorkflowMetadata = components["schemas"]["WorkflowMetadata"];

interface DataProviderInputsConfigProps {
	provider: WorkflowMetadata;
	inputs: Record<string, DataProviderInputConfig>;
	onChange: (inputs: Record<string, DataProviderInputConfig>) => void;
	availableFields?: string[]; // Field names available for reference
}

export function DataProviderInputsConfig({
	provider,
	inputs,
	onChange,
	availableFields = [],
}: DataProviderInputsConfigProps) {
	const id = useId();
	// No parameters means nothing to configure
	if (!provider.parameters || provider.parameters.length === 0) {
		return null;
	}

	const handleModeChange = (
		paramName: string,
		mode: DataProviderInputMode,
	) => {
		onChange({
			...inputs,
			[paramName]: {
				mode,
				value:
					mode === "static" ? inputs[paramName]?.value || "" : null,
				field_name:
					mode === "fieldRef"
						? inputs[paramName]?.field_name || null
						: null,
				expression:
					mode === "expression"
						? inputs[paramName]?.expression || ""
						: null,
			},
		});
	};

	const handleValueChange = (paramName: string, value: string) => {
		const currentMode = inputs[paramName]?.mode || "static";
		onChange({
			...inputs,
			[paramName]: {
				...inputs[paramName],
				mode: currentMode,
				value: currentMode === "static" ? value : null,
				field_name: currentMode === "fieldRef" ? value : null,
				expression: currentMode === "expression" ? value : null,
			},
		});
	};

	const getCurrentValue = (paramName: string): string => {
		const config = inputs[paramName];
		if (!config) return "";

		switch (config.mode) {
			case "static":
				return config.value || "";
			case "fieldRef":
				return config.field_name || "";
			case "expression":
				return config.expression || "";
			default:
				return "";
		}
	};

	return (
		<div className="min-w-0 space-y-4 rounded-[var(--bf-radius-surface)] border p-4">
			<div>
				<h4 className="text-sm font-semibold">Data Provider Inputs</h4>
				<p className="text-sm leading-6 text-muted-foreground mt-1">
					Configure input values for this data provider
				</p>
			</div>
			<div className="min-w-0 space-y-5">
				{provider.parameters.map((param) => {
					const currentMode = inputs[param.name]?.mode || "static";
					const currentValue = getCurrentValue(param.name);

					return (
						<div key={param.name} className="min-w-0 space-y-3">
							<div className="flex min-w-0 flex-col gap-3">
								<Label
									htmlFor={
										currentMode === "expression"
											? undefined
											: `${id}-${param.name}`
									}
									className="text-sm flex min-w-0 flex-wrap items-center gap-2 [overflow-wrap:anywhere]"
								>
									<span className="font-mono">
										{param.name}
									</span>
									{param.required && (
										<Badge
											variant="destructive"
											className="text-xs px-1.5 py-0"
										>
											Required
										</Badge>
									)}
								</Label>
								<ToggleGroup
									type="single"
									value={currentMode}
									onValueChange={(value) =>
										value &&
										handleModeChange(
											param.name,
											value as DataProviderInputMode,
										)
									}
									aria-label={`${param.name} input mode`}
									className="h-auto max-w-full flex-wrap gap-1"
								>
									<ToggleGroupItem
										value="static"
										className="min-h-11 h-auto flex-1 px-3 py-2 text-sm"
									>
										Static
									</ToggleGroupItem>
									<ToggleGroupItem
										value="fieldRef"
										className="min-h-11 h-auto flex-1 px-3 py-2 text-sm"
									>
										Field
									</ToggleGroupItem>
									<ToggleGroupItem
										value="expression"
										className="min-h-11 h-auto flex-1 px-3 py-2 text-sm"
									>
										Expression
									</ToggleGroupItem>
								</ToggleGroup>
							</div>

							{/* Static mode: text input */}
							{currentMode === "static" && (
								<Input
									id={`${id}-${param.name}`}
									aria-describedby={
										param.description
											? `${id}-${param.name}-help`
											: undefined
									}
									value={currentValue}
									onChange={(e) =>
										handleValueChange(
											param.name,
											e.target.value,
										)
									}
									placeholder={
										param.description ||
										`Enter ${param.label || param.name}...`
									}
									className="min-h-11 text-sm font-mono"
								/>
							)}

							{/* Field reference mode: dropdown */}
							{currentMode === "fieldRef" && (
								<Select
									value={currentValue}
									onValueChange={(value) =>
										handleValueChange(param.name, value)
									}
								>
									<SelectTrigger
										id={`${id}-${param.name}`}
										aria-describedby={
											param.description
												? `${id}-${param.name}-help`
												: undefined
										}
										className="min-h-11 text-sm data-[size=default]:h-auto [&_[data-slot=select-value]]:line-clamp-none [&_[data-slot=select-value]]:whitespace-normal [&_[data-slot=select-value]]:[overflow-wrap:anywhere]"
									>
										<SelectValue placeholder="Select a field to reference..." />
									</SelectTrigger>
									<SelectContent>
										{availableFields.length > 0 ? (
											availableFields.map((fieldName) => (
												<SelectItem
													key={fieldName}
													value={fieldName}
													className="min-h-11 font-mono text-sm [overflow-wrap:anywhere]"
												>
													{fieldName}
												</SelectItem>
											))
										) : (
											<SelectItem
												value="__none__"
												disabled
											>
												No fields available
											</SelectItem>
										)}
									</SelectContent>
								</Select>
							)}

							{/* Expression mode: Monaco editor with IntelliSense */}
							{currentMode === "expression" && (
								<ExpressionEditor
									label="Expression"
									value={currentValue}
									onChange={(value) =>
										handleValueChange(param.name, value)
									}
									helpText="JavaScript expression evaluated with form context (context.field, context.workflow, context.query)"
									height={120}
								/>
							)}

							{param.description && (
								<p
									id={`${id}-${param.name}-help`}
									className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]"
								>
									{param.description}
								</p>
							)}
						</div>
					);
				})}
			</div>
		</div>
	);
}
