import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { UploadState } from "@/stores/uploadStore";

interface EditorUploadStatusProps {
	state: UploadState;
	onCancel: () => void;
	onDismiss: () => void;
}

export function EditorUploadStatus({
	state,
	onCancel,
	onDismiss,
}: EditorUploadStatusProps) {
	const progress = state.totalCount
		? Math.min(
				100,
				Math.round((state.completedCount / state.totalCount) * 100),
			)
		: 0;
	const successCount = state.totalCount - state.failures.length;
	const title = state.isUploading
		? state.isCancelling
			? "Cancelling upload…"
			: `Uploading files · ${state.completedCount}/${state.totalCount}`
		: state.isCancelled
			? "Upload cancelled"
			: state.failures.length
				? `Uploaded ${successCount}/${state.totalCount} files · ${state.failures.length} failed`
				: `Uploaded ${successCount} file${successCount === 1 ? "" : "s"}`;
	return (
		<section
			aria-label="File upload status"
			className="min-w-0 flex-1 space-y-2 py-2"
		>
			<div className="flex min-w-0 items-start gap-2">
				<div className="min-w-0 flex-1 space-y-2">
					<p
						role="status"
						className="flex items-start gap-2 text-sm leading-5 sm:text-xs font-medium text-foreground"
					>
						{state.isUploading ? (
							<Loader2 className="mt-0.5 size-3 shrink-0 animate-spin motion-reduce:animate-none!" />
						) : state.failures.length || state.isCancelled ? (
							<AlertCircle className="mt-0.5 size-3 shrink-0 text-[var(--bf-warning)]" />
						) : (
							<CheckCircle className="mt-0.5 size-3 shrink-0 text-[var(--bf-success)]" />
						)}
						<span className="[overflow-wrap:anywhere]">
							{title}
						</span>
					</p>
					{state.isUploading && (
						<>
							<p className="font-mono text-sm leading-5 sm:text-xs [overflow-wrap:anywhere]">
								{state.currentFile || "Preparing files…"}
							</p>
							<Progress
								aria-label="File upload progress"
								value={progress}
								className="h-1.5"
							/>
						</>
					)}
				</div>
				<Button
					variant="ghost"
					className="min-h-11 h-auto shrink-0 px-3"
					disabled={state.isUploading && state.isCancelling}
					onClick={state.isUploading ? onCancel : onDismiss}
					aria-label={
						state.isUploading
							? "Cancel upload"
							: "Dismiss upload status"
					}
				>
					{state.isUploading ? "Cancel" : "Dismiss"}
				</Button>
			</div>
			{state.failures.length > 0 && (
				<details className="min-w-0">
					<summary className="min-h-11 cursor-pointer rounded-[var(--bf-radius-control)] py-3 text-sm leading-5 sm:text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
						Review {state.failures.length} failed{" "}
						{state.failures.length === 1 ? "file" : "files"}
					</summary>
					<ul
						aria-label="Upload failures"
						tabIndex={0}
						className="max-h-48 space-y-3 overflow-y-auto py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						{state.failures.map((failure, index) => (
							<li
								key={`${failure.path}-${index}`}
								className="min-w-0 space-y-1"
							>
								<p className="font-mono text-sm leading-5 sm:text-xs text-foreground [overflow-wrap:anywhere]">
									{failure.path}
								</p>
								<p className="text-sm leading-5 sm:text-xs text-destructive [overflow-wrap:anywhere]">
									{failure.error}
								</p>
							</li>
						))}
					</ul>
				</details>
			)}
		</section>
	);
}
