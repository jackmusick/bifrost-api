import { AlertCircle, AlertTriangle, CheckCircle2 } from "lucide-react";

export interface DocsIndexResponse {
	status: string;
	files_indexed: number;
	files_unchanged: number;
	files_deleted: number;
	duration_ms: number;
	message: string | null;
}

export interface AppDependencyIssue {
	app_id: string;
	app_name: string;
	app_slug: string;
	file_path: string;
	dependency_type: string;
	dependency_id: string;
}

export interface AppDependencyScanResponse {
	apps_scanned: number;
	files_scanned: number;
	dependencies_rebuilt: number;
	issues_found: number;
	issues: AppDependencyIssue[];
	notification_created: boolean;
}

function ScanMetrics({ values }: { values: { label: string; value: number | string }[] }) {
	return <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
		{values.map(({label, value}) => <div key={label} className="min-w-0"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums [overflow-wrap:anywhere]">{value}</dd></div>)}
	</dl>;
}

export function DocsIndexResults({ result }: { result: DocsIndexResponse }) {
	const complete = result.status === "complete";
	const skipped = result.status === "skipped";
	const Icon = complete ? CheckCircle2 : skipped ? AlertCircle : AlertTriangle;
	return <section aria-label="Documentation index results" className="min-w-0 space-y-4">
		<p className={`flex items-start gap-2 font-medium ${complete ? "text-[var(--bf-success)]" : skipped ? "text-[var(--bf-warning)]" : "text-destructive"}`}><Icon className="mt-0.5 size-5 shrink-0" />{complete ? "Indexing complete" : skipped ? "Indexing skipped" : "Indexing failed"}</p>
		{complete && <ScanMetrics values={[{label: "Indexed",value: result.files_indexed},{label: "Unchanged",value: result.files_unchanged},{label: "Deleted",value: result.files_deleted},{label: "Duration",value: result.duration_ms < 1000 ? `${result.duration_ms}ms` : `${(result.duration_ms / 1000).toFixed(1)}s`}]} />}
		{result.message && <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{result.message}</p>}
	</section>;
}

export function AppDepScanResults({ result }: { result: AppDependencyScanResponse }) {
	const groups = new Map<string, {name: string; issues: AppDependencyIssue[]}>();
	for (const issue of result.issues) {
		const group = groups.get(issue.app_slug) ?? {name: issue.app_name, issues: []};
		group.issues.push(issue);
		groups.set(issue.app_slug, group);
	}
	const hasIssues = result.issues_found > 0;
	const Icon = hasIssues ? AlertTriangle : CheckCircle2;
	return <section aria-label="App dependency scan results" className="min-w-0 space-y-5">
		<p className={`flex items-start gap-2 font-medium ${hasIssues ? "text-[var(--bf-warning)]" : "text-[var(--bf-success)]"}`}><Icon className="mt-0.5 size-5 shrink-0" />{hasIssues ? `${result.issues_found} broken reference${result.issues_found === 1 ? "" : "s"}` : "All dependencies valid"}</p>
		<ScanMetrics values={[{label: "Apps scanned",value: result.apps_scanned},{label: "Files scanned",value: result.files_scanned},{label: "Dependencies rebuilt",value: result.dependencies_rebuilt}]} />
		{hasIssues && <div className="space-y-3">
			<h4 className="text-sm font-medium">Missing workflow references</h4>
			<div role="region" aria-label="Missing workflow references" tabIndex={0} className="max-h-96 min-w-0 space-y-5 overflow-y-auto rounded-[var(--bf-radius-surface)] border p-4 outline-none focus-visible:ring-2 focus-visible:ring-ring">
				{Array.from(groups, ([slug, group]) => <section key={slug} className="min-w-0 space-y-3">
					<div><h5 className="text-sm font-semibold [overflow-wrap:anywhere]">{group.name}</h5><p className="mt-1 text-sm text-muted-foreground [overflow-wrap:anywhere]">{slug}</p></div>
					<ul className="divide-y">{group.issues.map((issue, index) => <li key={`${issue.dependency_id}-${index}`} className="space-y-2 py-3 first:pt-0 last:pb-0">
						<p className="font-mono text-sm [overflow-wrap:anywhere]">{issue.file_path}</p>
						<p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">Missing {issue.dependency_type}: <code className="text-destructive">{issue.dependency_id}</code></p>
					</li>)}</ul>
				</section>)}
			</div>
		</div>}
	</section>;
}
