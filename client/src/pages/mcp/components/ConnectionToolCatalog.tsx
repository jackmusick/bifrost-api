import { useId } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface ConnectionTool {
	id: string;
	tool_name: string;
	enabled: boolean;
	disabled_reason?: string | null;
}

function ToolRecord({
	tool,
	enabled,
	onChange,
}: {
	tool: ConnectionTool;
	enabled: boolean;
	onChange: (enabled: boolean) => void;
}) {
	const id = useId();
	return (
		<li className="min-w-0 border-b py-3 last:border-b-0">
			<div className="flex min-w-0 items-start gap-3">
				<div className="flex min-h-11 shrink-0 items-center">
					<Checkbox
						id={id}
						checked={enabled}
						onCheckedChange={(value) => onChange(value === true)}
						aria-describedby={
							tool.disabled_reason ? `${id}-reason` : undefined
						}
					/>
				</div>
				<div className="min-w-0 flex-1">
					<Label
						htmlFor={id}
						className="flex min-h-11 cursor-pointer items-center font-mono text-sm [overflow-wrap:anywhere]"
					>
						{tool.tool_name}
					</Label>
					{tool.disabled_reason && (
						<p
							id={`${id}-reason`}
							className="text-sm text-muted-foreground [overflow-wrap:anywhere]"
						>
							{tool.disabled_reason}
						</p>
					)}
				</div>
			</div>
		</li>
	);
}

export function ConnectionToolCatalog({
	tools,
	enabledMap,
	onChange,
}: {
	tools: ConnectionTool[];
	enabledMap: Record<string, boolean>;
	onChange: (id: string, enabled: boolean) => void;
}) {
	return (
		<ul aria-label="Connection tools" className="min-w-0">
			{tools.map((tool) => (
				<ToolRecord
					key={tool.id}
					tool={tool}
					enabled={enabledMap[tool.id] ?? tool.enabled}
					onChange={(enabled) => onChange(tool.id, enabled)}
				/>
			))}
		</ul>
	);
}
