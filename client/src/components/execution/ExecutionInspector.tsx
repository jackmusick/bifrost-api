import { useState, type ReactNode } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ExecutionInspector({
	input,
	output,
	details,
	completed,
}: {
	input: ReactNode;
	output: ReactNode;
	details: ReactNode;
	completed: boolean;
}) {
	const [selectedTab, setSelectedTab] = useState<string | null>(null);
	return (
		<aside
			aria-label="Run inspector"
			className="flex min-h-0 min-w-0 flex-col rounded-[var(--bf-radius-surface)] border bg-card p-4"
		>
			<h2 className="mb-4 text-base font-semibold">Run details</h2>
			<Tabs
				value={selectedTab ?? (completed ? "output" : "input")}
				onValueChange={setSelectedTab}
				className="min-h-0 min-w-0 xl:flex-1"
			>
				<TabsList aria-label="Run inspector content">
					<TabsTrigger value="output">Output</TabsTrigger>
					<TabsTrigger value="input">Input</TabsTrigger>
					<TabsTrigger value="details">Details</TabsTrigger>
				</TabsList>
				<TabsContent
					value="output"
					className="mt-4 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{output}
				</TabsContent>
				<TabsContent
					value="input"
					className="mt-4 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{input}
				</TabsContent>
				<TabsContent
					value="details"
					className="mt-4 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{details}
				</TabsContent>
			</Tabs>
		</aside>
	);
}
