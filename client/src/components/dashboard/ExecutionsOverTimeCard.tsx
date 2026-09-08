import { useReducedMotion } from "framer-motion";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { AlertCircle } from "lucide-react";
import {
	Card,
	CardAction,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	ChartContainer,
	ChartTooltip,
	ChartTooltipContent,
	type ChartConfig,
} from "@/components/ui/chart";
import { ExecutionChartData } from "./ExecutionChartData";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
	formatExecutionBuckets,
	type AggregatedExecutionBucket,
	type ChartWindow,
	type OutcomeSummary,
} from "@/lib/execution-buckets";

interface ExecutionsOverTimeCardProps {
	window: ChartWindow;
	onWindowChange: (window: ChartWindow) => void;
	buckets: readonly AggregatedExecutionBucket[] | undefined;
	/** Shared outcome tally — the same object the stat cards render. */
	outcomes: OutcomeSummary;
	isLoading: boolean;
	isError: boolean;
}

const chartConfig = {
	success: {
		label: "Success",
		color: "var(--bf-success)",
	},
	failed: {
		label: "Failed",
		color: "var(--destructive)",
	},
} satisfies ChartConfig;

export const WINDOW_LABELS: Record<ChartWindow, string> = {
	"24h": "Last 24 hours",
	"7d": "Last 7 days",
	"30d": "Last 30 days",
};

export function ExecutionsOverTimeCard({
	window,
	onWindowChange,
	buckets: aggregateBuckets,
	outcomes,
	isLoading,
	isError,
}: ExecutionsOverTimeCardProps) {
	const reducedMotion = useReducedMotion();
	const buckets = useMemo(
		() => formatExecutionBuckets(aggregateBuckets ?? [], window),
		[aggregateBuckets, window],
	);

	return (
		<Card>
			<CardHeader className="flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0">
					<CardTitle>Executions</CardTitle>
					<CardDescription>
						{isLoading || isError ? (
							WINDOW_LABELS[window]
						) : (
							<>
								{`${WINDOW_LABELS[window]} · ${outcomes.total.toLocaleString()} ${
									outcomes.total === 1 ? "run" : "runs"
								}`}
								{outcomes.failed > 0 && (
									<>
										{" · "}
										<Link
											to="/history?status=Failed"
											className="text-destructive transition-colors hover:underline"
										>
											{outcomes.failed.toLocaleString()}{" "}
											failed
										</Link>
									</>
								)}
							</>
						)}
					</CardDescription>
				</div>
				<CardAction>
					<ToggleGroup
						aria-label="Execution time window"
						type="single"
						value={window}
						onValueChange={(value) => {
							if (value) onWindowChange(value as ChartWindow);
						}}
						className="rounded-[var(--bf-radius-control)] bg-muted/50 p-0.5"
					>
						<ToggleGroupItem
							value="24h"
							aria-label="Last 24 hours"
							className="h-11 rounded-[var(--bf-radius-control)] px-3 text-xs sm:h-8"
						>
							24h
						</ToggleGroupItem>
						<ToggleGroupItem
							value="7d"
							aria-label="Last 7 days"
							className="h-11 rounded-[var(--bf-radius-control)] px-3 text-xs sm:h-8"
						>
							7d
						</ToggleGroupItem>
						<ToggleGroupItem
							value="30d"
							aria-label="Last 30 days"
							className="h-11 rounded-[var(--bf-radius-control)] px-3 text-xs sm:h-8"
						>
							30d
						</ToggleGroupItem>
					</ToggleGroup>
				</CardAction>
			</CardHeader>
			<CardContent>
				{isLoading ? (
					<Skeleton className="h-[220px] w-full" />
				) : isError ? (
					<div
						className="flex h-[220px] flex-col items-center justify-center gap-2 text-center"
						data-testid="executions-chart-error"
					>
						<AlertCircle className="h-6 w-6 text-destructive" />
						<p className="text-sm text-muted-foreground">
							Couldn't load executions for this window.
						</p>
					</div>
				) : outcomes.total === 0 ? (
					<div
						className="flex h-[220px] flex-col items-center justify-center gap-1 text-center"
						data-testid="executions-chart-empty"
					>
						<p className="text-sm font-medium">
							No executions in this window
						</p>
						<p className="text-sm text-muted-foreground">
							Runs will chart here as workflows execute.
						</p>
					</div>
				) : (
					<>
						<ChartContainer
							config={chartConfig}
							className="aspect-auto h-[220px] w-full"
						>
							<AreaChart
								data={buckets}
								margin={{
									top: 8,
									right: 8,
									bottom: 0,
									left: 0,
								}}
							>
								<defs>
									<linearGradient
										id="fillSuccess"
										x1="0"
										y1="0"
										x2="0"
										y2="1"
									>
										<stop
											offset="5%"
											stopColor="var(--color-success)"
											stopOpacity={0.5}
										/>
										<stop
											offset="95%"
											stopColor="var(--color-success)"
											stopOpacity={0.05}
										/>
									</linearGradient>
									<linearGradient
										id="fillFailed"
										x1="0"
										y1="0"
										x2="0"
										y2="1"
									>
										<stop
											offset="5%"
											stopColor="var(--color-failed)"
											stopOpacity={0.5}
										/>
										<stop
											offset="95%"
											stopColor="var(--color-failed)"
											stopOpacity={0.05}
										/>
									</linearGradient>
								</defs>
								<CartesianGrid vertical={false} />
								<XAxis
									dataKey="label"
									tickLine={false}
									axisLine={false}
									tickMargin={8}
									minTickGap={24}
								/>
								<YAxis
									allowDecimals={false}
									width={32}
									tickLine={false}
									axisLine={false}
								/>
								<ChartTooltip
									cursor={false}
									content={
										<ChartTooltipContent indicator="line" />
									}
								/>
								<Area
									isAnimationActive={!reducedMotion}
									animationDuration={220}
									dataKey="success"
									type="monotone"
									stroke="var(--color-success)"
									strokeWidth={2}
									fill="url(#fillSuccess)"
								/>
								<Area
									isAnimationActive={!reducedMotion}
									animationDuration={220}
									dataKey="failed"
									type="monotone"
									stroke="var(--color-failed)"
									strokeWidth={2}
									fill="url(#fillFailed)"
								/>
							</AreaChart>
						</ChartContainer>
						<ExecutionChartData buckets={buckets} />
					</>
				)}
			</CardContent>
		</Card>
	);
}
