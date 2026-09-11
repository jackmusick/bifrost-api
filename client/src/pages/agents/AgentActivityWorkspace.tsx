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
	return (
		<section
			data-slot="run-activity"
			aria-label="Agent activity workspace"
			className="flex min-w-0 flex-col gap-3 lg:min-h-0 lg:flex-1"
		>
			<div className="flex shrink-0 items-center justify-between gap-3">
				<p className="text-sm text-muted-foreground">
					{advanced
						? "Recorded inputs, outputs, and executor events"
						: "Expand delegated work. Select a call to inspect its result."}
				</p>
				<Button
					variant={advanced ? "secondary" : "ghost"}
					aria-pressed={advanced}
					onClick={() => setAdvanced(!advanced)}
					className="shrink-0"
				>
					<Code2 className="size-4" />
					Advanced
				</Button>
			</div>
			{advanced ? (
				<div
					className="min-w-0 space-y-5 pb-5 lg:min-h-0 lg:flex-1 lg:overflow-auto"
					role="region"
					aria-label="Advanced activity"
				>
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
				/>
			)}
		</section>
	);
}
