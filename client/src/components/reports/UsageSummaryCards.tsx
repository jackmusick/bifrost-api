import { DollarSign, Hash, Cpu, HardDrive } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { UsageReportResponse } from "@/services/usage";
import {
	formatCurrency,
	formatNumber,
	formatCpuSeconds,
	formatBytes,
} from "./formatters";

export interface UsageSummaryCardsProps {
	data: UsageReportResponse | null | undefined;
	isLoading: boolean;
}

export function UsageSummaryCards({ data, isLoading }: UsageSummaryCardsProps) {
	return (
		<div className="grid gap-3 min-[360px]:grid-cols-2 xl:grid-cols-4">
			{/* Total AI Cost */}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2">
					<CardTitle className="text-sm font-medium">
						Total AI Cost
					</CardTitle>
					<DollarSign className="h-4 w-4 text-muted-foreground" />
				</CardHeader>
				<CardContent className="px-4">
					{isLoading ? (
						<Skeleton className="h-8 w-24" />
					) : (
						<div className="text-xl sm:text-2xl font-semibold tabular-nums [overflow-wrap:anywhere]">
							{formatCurrency(data?.summary?.total_ai_cost)}
						</div>
					)}
					<p className="text-xs text-muted-foreground">
						USD spent on AI APIs
					</p>
				</CardContent>
			</Card>

			{/* Total Tokens */}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2">
					<CardTitle className="text-sm font-medium">
						Total Tokens
					</CardTitle>
					<Hash className="h-4 w-4 text-muted-foreground" />
				</CardHeader>
				<CardContent className="px-4">
					{isLoading ? (
						<Skeleton className="h-8 w-24" />
					) : (
						<div className="text-xl sm:text-2xl font-semibold tabular-nums [overflow-wrap:anywhere]">
							{formatNumber(
								(data?.summary?.total_input_tokens ?? 0) +
									(data?.summary?.total_output_tokens ?? 0),
							)}
						</div>
					)}
					<p className="text-xs text-muted-foreground">
						Input + output tokens
					</p>
				</CardContent>
			</Card>

			{/* Total CPU Seconds */}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2">
					<CardTitle className="text-sm font-medium">
						Total CPU Time
					</CardTitle>
					<Cpu className="h-4 w-4 text-muted-foreground" />
				</CardHeader>
				<CardContent className="px-4">
					{isLoading ? (
						<Skeleton className="h-8 w-24" />
					) : (
						<div className="text-xl sm:text-2xl font-semibold tabular-nums [overflow-wrap:anywhere]">
							{formatCpuSeconds(data?.summary?.total_cpu_seconds)}
						</div>
					)}
					<p className="text-xs text-muted-foreground">
						Execution compute time
					</p>
				</CardContent>
			</Card>

			{/* Peak Memory */}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2">
					<CardTitle className="text-sm font-medium">
						Peak Memory
					</CardTitle>
					<HardDrive className="h-4 w-4 text-muted-foreground" />
				</CardHeader>
				<CardContent className="px-4">
					{isLoading ? (
						<Skeleton className="h-8 w-24" />
					) : (
						<div className="text-xl sm:text-2xl font-semibold tabular-nums [overflow-wrap:anywhere]">
							{formatBytes(data?.summary?.peak_memory_bytes)}
						</div>
					)}
					<p className="text-xs text-muted-foreground">
						Maximum memory usage
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
