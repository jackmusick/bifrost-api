interface AppLoadingSkeletonProps {
	message?: string;
	appName?: string | null;
	appLogo?: string | null;
}

function appInitial(name: string | null | undefined) {
	const trimmed = name?.trim();
	return trimmed ? trimmed.slice(0, 1).toUpperCase() : "B";
}

/** Shared loading feedback for apps whose layout is not known until mounting. */
export function AppLoadingSkeleton({
	message,
	appName,
	appLogo,
}: AppLoadingSkeletonProps) {
	const label =
		message ?? (appName ? `Opening ${appName}…` : "Loading application…");

	return (
		<div className="flex h-full min-h-48 w-full items-center justify-center bg-background p-[var(--bf-surface-pad)]">
			<div
				role="status"
				aria-label={label}
				className="w-full max-w-sm rounded-[var(--bf-radius-surface)] border border-border/70 bg-card/80 px-5 py-5 shadow-sm"
			>
				<div className="flex items-center gap-3">
					<div className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-[var(--bf-radius-feature)] border border-border bg-background text-base font-semibold text-foreground shadow-sm">
						{appLogo ? (
							<img
								src={appLogo}
								alt=""
								className="h-full w-full object-cover"
							/>
						) : (
							<span aria-hidden="true">
								{appInitial(appName)}
							</span>
						)}
					</div>
					<div className="min-w-0 flex-1">
						<p className="truncate text-sm font-medium text-foreground">
							{appName ?? "Application"}
						</p>
						<p className="mt-0.5 text-sm text-muted-foreground [overflow-wrap:anywhere]">
							{label}
						</p>
					</div>
				</div>
				<div
					aria-hidden="true"
					className="route-transition-progress-track mt-4 h-0.5 overflow-hidden rounded-full motion-reduce:h-px"
				>
					<div
						data-state="loading"
						className="route-transition-progress-fill h-full w-full shadow-none motion-reduce:animate-none"
					/>
				</div>
			</div>
		</div>
	);
}
