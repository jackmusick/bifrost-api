import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

const fields = [
	["context.parameters", "Input parameters, including event data"],
	['context.parameters["_event"]', "Webhook metadata"],
	["context.org_id", "Organization scope"],
	["context.email", "Caller email"],
	["context.roi.time_saved", "ROI tracking"],
];

export function ExecutionContextHelp() {
	return (
		<Popover>
			<PopoverTrigger asChild>
				<Button
					variant="ghost"
					size="icon-lg"
					className="shrink-0 text-muted-foreground"
					aria-label="About execution context"
				>
					<Info className="size-4" />
				</Button>
			</PopoverTrigger>
			<PopoverContent
				align="end"
				side="bottom"
				collisionPadding={16}
				className="w-80 max-w-[calc(100vw-2rem)] max-h-[var(--radix-popover-content-available-height)] overflow-y-auto"
			>
				<h5 className="text-sm font-semibold">
					Using execution context
				</h5>
				<code className="my-3 block text-sm [overflow-wrap:anywhere]">
					from bifrost import context
				</code>
				<dl className="space-y-3">
					{fields.map(([name, description]) => (
						<div key={name}>
							<dt className="font-mono text-sm text-primary [overflow-wrap:anywhere]">
								{name}
							</dt>
							<dd className="mt-1 text-sm text-muted-foreground">
								{description}
							</dd>
						</div>
					))}
				</dl>
			</PopoverContent>
		</Popover>
	);
}
