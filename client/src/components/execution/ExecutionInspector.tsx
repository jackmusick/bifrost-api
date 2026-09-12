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
			className={cn("min-w-0 pb-4", className)}
		>
			<Tabs
				value={currentTab}
				onValueChange={handleTabChange}
				className="min-w-0 gap-1"
			>
				<div className="min-w-0">
					<TabsList
						variant="line"
						aria-label="Execution content tabs"
						className="w-fit max-w-full justify-start gap-3"
					>
						<TabsTrigger value="result">Result</TabsTrigger>
						<TabsTrigger value="input">Input</TabsTrigger>
						<TabsTrigger value="logs">Logs</TabsTrigger>
					</TabsList>
				</div>
				<TabsContent value="result" className="mt-0 min-w-0">
					{result}
				</TabsContent>
				<TabsContent value="input" className="mt-0 min-w-0">
					{input}
				</TabsContent>
				<TabsContent value="logs" className="mt-0 min-w-0">
					{logs}
				</TabsContent>
			</Tabs>
			{summary && (
				<div className="mt-6 min-w-0 border-t pt-4">{summary}</div>
			)}
		</aside>
	);
}
