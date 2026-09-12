import type { ReactNode } from "react";
import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { BundleMessage } from "@/services/websocket";

export function BundleLoadFailure({
	error,
	onRetry,
}: {
	error: string;
	onRetry: () => void;
}) {
	return (
		<div className="flex min-h-64 h-full items-center justify-center p-4 sm:p-6">
			<section className="min-w-0 w-full max-w-xl space-y-4 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]">
				<div role="alert" className="space-y-2">
					<AlertTriangle
						aria-hidden="true"
						className="size-6 text-destructive"
					/>
					<h2 className="font-display text-xl font-semibold">
						Bundle Load Error
					</h2>
					<p className="text-sm text-muted-foreground">
						The app could not start. Try reloading it.
					</p>
				</div>
				<Button
					type="button"
					className="min-h-11 w-full sm:w-auto"
					onClick={onRetry}
				>
					<RefreshCw aria-hidden="true" className="size-4" />
					Reload app
				</Button>
				<details className="min-w-0 border-t pt-2">
					<summary className="min-h-11 cursor-pointer rounded-[var(--bf-radius-control)] py-3 text-sm text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
						Technical details
					</summary>

					<pre
						tabIndex={0}
						aria-label="Bundle error details"
						className="max-h-64 overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere] rounded-[var(--bf-radius-control)] bg-muted/30 p-3 font-mono text-xs leading-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						{error}
					</pre>
				</details>
			</section>
		</div>
	);
}

function BundleNotice({
	title,
	dismissLabel,
	onDismiss,
	children,
	error = false,
}: {
	title: string;
	dismissLabel: string;
	onDismiss: () => void;
	children: ReactNode;
	error?: boolean;
}) {
	return (
		<section className="min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border bg-card p-[var(--bf-surface-pad)]">
			<div className="sticky top-0 z-10 flex items-start justify-between gap-3 bg-card">
				<h3
					role={error ? "alert" : "status"}
					className={
						error
							? "min-w-0 pt-2 text-sm font-semibold text-destructive [overflow-wrap:anywhere]"
							: "min-w-0 pt-2 text-sm font-semibold [overflow-wrap:anywhere]"
					}
				>
					{title}
				</h3>
				<Button
					type="button"
					variant="ghost"
					size="icon-lg"
					aria-label={dismissLabel}
					onClick={onDismiss}
				>
					<X aria-hidden="true" className="size-4" />
				</Button>
			</div>
			{children}
		</section>
	);
}

export function AutoMigrateNotice({ onDismiss }: { onDismiss: () => void }) {
	return (
		<BundleNotice
			title="App updated for new runtime"
			dismissLabel="Dismiss runtime update notice"
			onDismiss={onDismiss}
		>
			<p className="text-sm leading-6 text-muted-foreground">
				Your app was automatically updated to the new runtime. Review
				the changes in your workspace on your next{" "}
				<code className="font-mono text-xs text-foreground">
					bifrost pull
				</code>
				.
			</p>
		</BundleNotice>
	);
}

function BuildErrorList({ errors }: { errors: BundleMessage[] }) {
	return (
		<ul className="space-y-3 text-xs leading-6">
			{errors.map((error, index) => (
				<li key={index} className="font-mono [overflow-wrap:anywhere]">
					{error.file && (
						<p className="font-semibold">
							{error.file}
							{error.line != null ? `:${error.line}` : ""}
							{error.column != null ? `:${error.column}` : ""}
						</p>
					)}
					<p className="whitespace-pre-wrap text-muted-foreground">
						{error.text}
					</p>
				</li>
			))}
		</ul>
	);
}

export function BuildErrorBanner({
	errors,
	onDismiss,
}: {
	errors: BundleMessage[];
	onDismiss: () => void;
}) {
	return (
		<BundleNotice
			title="Build failed — showing last good bundle"
			dismissLabel="Dismiss build errors"
			onDismiss={onDismiss}
			error
		>
			<BuildErrorList errors={errors.slice(0, 5)} />
			{errors.length > 5 && (
				<details>
					<summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
						Show {errors.length - 5} more errors
					</summary>
					<BuildErrorList errors={errors.slice(5)} />
				</details>
			)}
		</BundleNotice>
	);
}

export function BundleNoticeStack({ children }: { children: ReactNode }) {
	return (
		<div className="absolute inset-x-3 top-3 z-50 flex max-h-[min(28rem,calc(100%-1.5rem))] flex-col gap-3 overflow-y-auto">
			{children}
		</div>
	);
}
