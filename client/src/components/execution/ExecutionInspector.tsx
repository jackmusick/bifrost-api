import { useState, type ReactNode } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export function ExecutionInspector({
	input,
	result,
	logs,
	summary,
	defaultTab = "result",
	value,
	onValueChange,
	className,
}: {
	input: ReactNode;
	result: ReactNode;
	logs: ReactNode;
	summary?: ReactNode;
	defaultTab?: "result" | "input" | "logs";
	value?: "result" | "input" | "logs";
	onValueChange?: (value: "result" | "input" | "logs") => void;
	className?: string;
}) {
	const [selectedTab, setSelectedTab] = useState<string | null>(null);
	const currentTab = value ?? selectedTab ?? defaultTab;
	const handleTabChange = (nextValue: string) => {
		if (
			nextValue === "result" ||
			nextValue === "input" ||
			nextValue === "logs"
		) {
			onValueChange?.(nextValue);
		}
		if (!value) {
			setSelectedTab(nextValue);
		}
	};
	return (
		<aside
			aria-label="Execution content"
			className={cn(
				"flex min-h-0 min-w-0 flex-col rounded-[var(--bf-radius-surface)] border bg-card p-4",
				className,
			)}
		>
			<Tabs
				value={currentTab}
				onValueChange={handleTabChange}
				className="min-h-0 min-w-0 xl:flex-1"
			>
				<div className="mb-4 min-w-0">
					<TabsList aria-label="Execution content tabs">
						<TabsTrigger value="result">Result</TabsTrigger>
						<TabsTrigger value="input">Input</TabsTrigger>
						<TabsTrigger value="logs">Logs</TabsTrigger>
					</TabsList>
				</div>
				<TabsContent
					value="result"
					className="mt-0 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{result}
				</TabsContent>
				<TabsContent
					value="input"
					className="mt-0 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{input}
				</TabsContent>
				<TabsContent
					value="logs"
					className="mt-0 min-h-0 min-w-0 xl:flex-1 xl:overflow-auto"
				>
					{logs}
				</TabsContent>
			</Tabs>
			{summary && <div className="mt-4 min-w-0">{summary}</div>}
		</aside>
	);
}
