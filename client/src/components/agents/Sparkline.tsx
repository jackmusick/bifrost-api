import { useId } from "react";

import { cn } from "@/lib/utils";

export interface SparklineProps {
	values: number[];
	className?: string;
	/** Tailwind text-* class, e.g. "text-emerald-400". Drives both line + fill gradient. */
	colorClass?: string;
	strokeWidth?: number;
	/** Optional accessible name for the chart. */
	ariaLabel?: string;
	/** Optional message shown when fewer than 2 points are available. */
	emptyLabel?: string;
}

/**
 * Inline-SVG area sparkline. No recharts dependency.
 * Provides an accessible image label when data is present and a small empty
 * state when the caller does not have enough points to draw a trend.
 */
export function Sparkline({
	values,
	className,
	colorClass = "text-primary",
	strokeWidth = 1.5,
	ariaLabel,
	emptyLabel,
}: SparklineProps) {
	const baseId = useId();
	const gradientId = `${baseId}-gradient`;
	const titleId = `${baseId}-title`;
	const descId = `${baseId}-desc`;
	if (values.length < 2) {
		if (!emptyLabel) return null;
		return (
			<div
				className={cn(
					"flex h-full w-full items-center justify-center rounded-[var(--bf-radius-surface)] border border-dashed border-border bg-muted/20 px-3 text-center text-[11px] text-muted-foreground",
					className,
				)}
				role="status"
				aria-live="polite"
				aria-label={emptyLabel}
			>
				{emptyLabel}
			</div>
		);
	}

	const w = 100;
	const h = 30;
	const max = Math.max(...values);
	const min = Math.min(...values);
	const range = Math.max(max - min, 1);
	const step = w / (values.length - 1);

	const points = values
		.map((v, i) => {
			const x = i * step;
			const y = h - ((v - min) / range) * h;
			return `${x.toFixed(2)},${y.toFixed(2)}`;
		})
		.join(" ");

	const areaPath = `M0,${h} L${points.split(" ").join(" L")} L${w},${h} Z`;
	const chartLabel =
		ariaLabel ?? summarizeSparkline(values, min, max);

	return (
		<svg
			viewBox={`0 0 ${w} ${h}`}
			preserveAspectRatio="none"
			className={cn("h-full w-full", colorClass, className)}
			role="img"
			aria-labelledby={titleId}
			aria-describedby={descId}
		>
			<title id={titleId}>{chartLabel}</title>
			<desc id={descId}>
				Trend area chart from {formatSparklineValue(values[0])} to{" "}
				{formatSparklineValue(values[values.length - 1])}. Range{" "}
				{formatSparklineValue(min)} to {formatSparklineValue(max)} across{" "}
				{values.length} points.
			</desc>
			<defs>
				<linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
					<stop offset="0%" stopColor="currentColor" stopOpacity={0.35} />
					<stop offset="100%" stopColor="currentColor" stopOpacity={0} />
				</linearGradient>
			</defs>
			<path d={areaPath} fill={`url(#${gradientId})`} />
			<polyline
				points={points}
				fill="none"
				stroke="currentColor"
				strokeWidth={strokeWidth}
				strokeLinejoin="round"
				strokeLinecap="round"
			/>
		</svg>
	);
}

function summarizeSparkline(values: number[], min: number, max: number) {
	const first = values[0];
	const last = values[values.length - 1];
	const direction =
		last > first ? "rising" : last < first ? "falling" : "steady";
	return `Trend chart with ${values.length} points, ${direction} from ${formatSparklineValue(first)} to ${formatSparklineValue(last)}, low ${formatSparklineValue(min)} and high ${formatSparklineValue(max)}.`;
}

function formatSparklineValue(value: number) {
	if (!Number.isFinite(value)) return "0";
	return new Intl.NumberFormat("en-US", {
		maximumFractionDigits: 2,
	}).format(value);
}
