interface AppLoadingSkeletonProps {
	message?: string;
}

/** Shared loading feedback for apps whose layout is not known until mounting. */
export function AppLoadingSkeleton({
	message = "Loading application...",
}: AppLoadingSkeletonProps) {
	return (
		<div className="flex min-h-48 h-full w-full items-center justify-center bg-background p-[var(--bf-surface-pad)]">
			<div
				role="status"
				aria-label={message}
				className="w-full max-w-sm space-y-4"
			>
				<p className="text-center text-sm text-muted-foreground [overflow-wrap:anywhere]">
					{message}
				</p>
				<div
					aria-hidden="true"
					className="route-transition-progress-track h-0.5 overflow-hidden rounded-full"
				>
					<div
						data-state="loading"
						className="route-transition-progress-fill h-full w-full shadow-none"
					/>
				</div>
			</div>
		</div>
	);
}
