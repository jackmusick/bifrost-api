import { useMemo } from "react";
import { Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCost, formatNumber } from "@/lib/utils";
import type { components } from "@/lib/v1";

type Run = components["schemas"]["AgentRunDetailResponse"];

export function RunAIUsageCard({
	usage,
	totals,
	reported,
	presentation = "card",
}: {
	usage: NonNullable<Run["ai_usage"]>;
	totals: Run["ai_totals"] | null;
	reported?: { model: string | null; tokens: number };
	presentation?: "card" | "embedded";
}) {
	const grouped = useMemo(() => {
		const rows = new Map<
			string,
			{
				model: string;
				calls: number;
				input: number;
				output: number;
				cost: number;
			}
		>();
		for (const entry of usage) {
			const row = rows.get(entry.model) ?? {
				model: entry.model,
				calls: 0,
				input: 0,
				output: 0,
				cost: 0,
			};
			row.calls++;
			row.input += entry.input_tokens;
			row.output += entry.output_tokens;
			row.cost += Number(entry.cost) || 0;
			rows.set(entry.model, row);
		}
		return [...rows.values()];
	}, [usage]);
	const content = (
		<>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<Sparkles className="h-4 w-4 text-primary" />
					AI Usage
				</CardTitle>
			</CardHeader>
			<CardContent className="min-w-0 space-y-4">
				{grouped.length === 0 && reported ? (
					<dl className="space-y-3 text-xs">
						{reported.model ? (
							<div>
								<dt className="text-muted-foreground">Model</dt>
								<dd className="mt-1 font-mono [overflow-wrap:anywhere]">
									{reported.model}
								</dd>
							</div>
						) : null}
						<div>
							<dt className="text-muted-foreground">Tokens</dt>
							<dd className="mt-1 tabular-nums">
								{formatNumber(reported.tokens)}
							</dd>
						</div>
					</dl>
				) : null}
				<ul className="divide-y">
					{grouped.map((row) => (
						<li
							key={row.model}
							className="min-w-0 space-y-3 py-3 first:pt-0"
						>
							<p className="font-mono text-xs [overflow-wrap:anywhere]">
								{row.model}
							</p>
							<UsageMetrics
								calls={row.calls}
								input={row.input}
								output={row.output}
								cost={row.cost}
							/>
						</li>
					))}
				</ul>
				{totals ? (
					<div className="space-y-3 border-t pt-3">
						<p className="text-xs font-medium">Total</p>
						<UsageMetrics
							calls={totals.call_count}
							input={totals.total_input_tokens}
							output={totals.total_output_tokens}
							cost={totals.total_cost}
						/>
					</div>
				) : null}
			</CardContent>
		</>
	);
	if (presentation === "embedded") {
		return (
			<div
				data-testid="ai-usage-card"
				className="[&_[data-slot=card-content]]:px-0 [&_[data-slot=card-header]]:px-0"
			>
				{content}
			</div>
		);
	}
	return <Card data-testid="ai-usage-card">{content}</Card>;
}

function UsageMetrics({
	calls,
	input,
	output,
	cost,
}: {
	calls: number;
	input: number;
	output: number;
	cost: number | string;
}) {
	return (
		<dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
			{[
				["Calls", formatNumber(calls)],
				["Cost", formatCost(cost)],
				["Input tokens", formatNumber(input)],
				["Output tokens", formatNumber(output)],
			].map(([label, value]) => (
				<div key={label} className="min-w-0">
					<dt className="text-muted-foreground">{label}</dt>
					<dd className="mt-1 font-mono tabular-nums [overflow-wrap:anywhere]">
						{value}
					</dd>
				</div>
			))}
		</dl>
	);
}
