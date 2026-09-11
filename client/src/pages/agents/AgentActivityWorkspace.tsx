import { useState, type ComponentProps } from "react";
import { Code2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Timeline, AdvancedTimeline } from "@/components/agents/Timeline";
import { RunPayloads } from "@/components/agents/RunReviewPanel";
import type { components } from "@/lib/v1";

type Run = components["schemas"]["AgentRunDetailResponse"];
export function AgentActivityWorkspace({
	run,
	...timelineProps
}: { run: Run } & Omit<ComponentProps<typeof Timeline>, "steps">) {
	const [advanced, setAdvanced] = useState(false);
	const advancedControl = (
		<Button
			variant={advanced ? "secondary" : "ghost"}
			aria-pressed={advanced}
			onClick={() => setAdvanced(!advanced)}
			className="ml-auto min-h-11 shrink-0 text-xs"
		>
			<Code2 className="size-4" />
			Advanced
		</Button>
	);
	return (
		<section
			data-slot="run-activity"
			aria-label="Agent activity workspace"
			className="flex min-w-0 flex-col gap-3 lg:min-h-0 lg:flex-1"
		>
			{advanced ? (
				<div
					className="min-w-0 space-y-5 pb-5 lg:min-h-0 lg:flex-1 lg:overflow-auto"
					role="region"
					aria-label="Advanced activity"
				>
					<div className="flex justify-end border-b border-border/60 pb-2">
						{advancedControl}
					</div>
					<RunPayloads input={run.input} output={run.output} />
					<h3 className="text-sm font-semibold">
						Raw executor trace
					</h3>
					<AdvancedTimeline steps={run.steps ?? []} />
				</div>
			) : (
				<Timeline
					{...timelineProps}
					steps={run.steps ?? []}
					inspector="inline"
					toolbarActions={advancedControl}
				/>
			)}
		</section>
	);
}
