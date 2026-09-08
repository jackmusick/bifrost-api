import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useReducedMotion } from "framer-motion";
import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
	Legend,
} from "recharts";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { UsageTrend } from "@/services/usage";
import {
	formatChartDateLabel,
	formatChartDateTick,
	formatCurrency,
	formatNumber,
} from "./formatters";

export interface UsageChartsProps {
	trends: UsageTrend[] | undefined;
	isLoading: boolean;
}

export function UsageCharts({ trends, isLoading }: UsageChartsProps) {
	const reducedMotion = useReducedMotion();
	const wideChart = useMediaQuery("(min-width: 640px)");
	return (
		<Card>
			<CardHeader>
				<CardTitle>Cost Over Time</CardTitle>
				<CardDescription>
					AI cost trends during the selected period
				</CardDescription>
			</CardHeader>
			<CardContent>
				{isLoading ? (
					<Skeleton className="h-[300px] w-full" />
				) : trends && trends.length > 0 ? (
					<ResponsiveContainer width="100%" height={300}>
						<LineChart data={trends}>
							<CartesianGrid
								strokeDasharray="3 3"
								className="stroke-muted"
							/>
							<XAxis
								minTickGap={24}
								dataKey="date"
								className="text-xs"
								tick={{
									fontSize: 12,
									fill: "var(--muted-foreground)",
								}}
								tickLine={false}
								axisLine={{ stroke: "var(--border)" }}
								tickFormatter={formatChartDateTick}
							/>
							<YAxis
								width={wideChart ? 64 : 42}
								className="text-xs"
								tick={{
									fontSize: 12,
									fill: "var(--muted-foreground)",
								}}
								tickLine={false}
								axisLine={{ stroke: "var(--border)" }}
								tickFormatter={(value) => `$${value}`}
								label={
									wideChart
										? {
												value: "Cost (USD)",
												angle: -90,
												position: "insideLeft",
												fontSize: 12,
												fill: "var(--muted-foreground)",
											}
										: undefined
								}
							/>
							<Tooltip
								contentStyle={{
									backgroundColor: "var(--popover)",
									border: "1px solid var(--border)",
									borderRadius: "var(--bf-radius-surface)",
									color: "var(--popover-foreground)",
								}}
								formatter={(value, name) => {
									if (name === "ai_cost")
										return [
											formatCurrency(
												value as string | number,
											),
											"AI Cost",
										];
									return [
										formatNumber(value as number),
										name as string,
									];
								}}
								labelFormatter={formatChartDateLabel}
							/>
							<Legend
								formatter={(value) => {
									if (value === "ai_cost") return "AI Cost";
									if (value === "input_tokens")
										return "Input Tokens";
									if (value === "output_tokens")
										return "Output Tokens";
									return value;
								}}
							/>
							<Line
								isAnimationActive={!reducedMotion}
								animationDuration={220}
								type="monotone"
								dataKey="ai_cost"
								stroke="var(--primary)"
								strokeWidth={2}
								dot={false}
								activeDot={{ r: 5 }}
							/>
						</LineChart>
					</ResponsiveContainer>
				) : (
					<div className="flex items-center justify-center h-[300px] text-muted-foreground">
						No trend data available for this period
					</div>
				)}
			</CardContent>
		</Card>
	);
}
