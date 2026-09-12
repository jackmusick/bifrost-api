import type { ExecutionBucket } from "@/lib/execution-buckets";

/** Text equivalent of the chart, readable by touch and assistive technology. */
export function ExecutionChartData({
	buckets,
}: {
	buckets: readonly ExecutionBucket[];
}) {
	return (
		<details className="mt-4 border-t pt-2">
			<summary className="min-h-11 cursor-pointer rounded-[var(--bf-radius-control)] py-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
				View execution data
			</summary>
			<ol
				aria-label="Execution counts by period"
				className="max-h-80 overflow-y-auto divide-y"
			>
				{buckets.map((bucket, index) => (
					<li
						key={`${bucket.start.toISOString()}-${index}`}
						className="space-y-2 py-3 text-sm"
					>
						<time
							dateTime={bucket.start.toISOString()}
							className="block font-medium"
						>
							{bucket.start.toLocaleString(undefined, {
								dateStyle: "medium",
								timeStyle: "short",
							})}
						</time>
						<dl className="grid grid-cols-2 gap-3">
							<div>
								<dt className="text-muted-foreground">
									Succeeded
								</dt>
								<dd className="font-mono tabular-nums">
									{bucket.success.toLocaleString()}
								</dd>
							</div>
							<div>
								<dt className="text-muted-foreground">
									Failed
								</dt>
								<dd className="font-mono tabular-nums">
									{bucket.failed.toLocaleString()}
								</dd>
							</div>
						</dl>
					</li>
				))}
			</ol>
		</details>
	);
}
