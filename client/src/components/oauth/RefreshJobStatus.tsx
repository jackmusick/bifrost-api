import { useOAuthRefreshJobStatus } from "@/hooks/useOAuth";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { CheckCircle2, XCircle, FileText, AlertCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

interface RefreshJobStatusProps {
	className?: string;
}

export function RefreshJobStatus({ className }: RefreshJobStatusProps) {
	const { data: jobStatus, isLoading, isError: isReadError, isFetching, refetch } = useOAuthRefreshJobStatus();

	if (isReadError && !jobStatus) {
		return <Card className={cn("rounded-[var(--bf-radius-surface)]", className)}>
			<CardHeader><CardTitle>Token Refresh Job</CardTitle></CardHeader>
			<CardContent className="space-y-3">
				<p role="alert" className="text-sm text-[var(--bf-danger)]">Unable to load token refresh status.</p>
				<Button variant="outline" className="min-h-11" disabled={isFetching} onClick={() => void refetch()}>{isFetching ? "Retrying..." : "Retry"}</Button>
			</CardContent>
		</Card>;
	}

	if (isLoading) {
		return (
			<Card className={cn("overflow-hidden rounded-[var(--bf-radius-surface)] border-border/70 bg-card shadow-sm", className)}>
				<CardHeader className="pb-3">
					<CardTitle className="text-sm font-medium leading-6">
						Token Refresh Job
					</CardTitle>
					<CardDescription className="text-sm leading-6 text-muted-foreground">
						Loading status...
					</CardDescription>
				</CardHeader>
			</Card>
		);
	}

	if (!jobStatus) {
		return (
			<Card className={cn("overflow-hidden rounded-[var(--bf-radius-surface)] border-border/70 bg-card shadow-sm", className)}>
				<CardHeader className="pb-3">
					<CardTitle className="text-sm font-medium leading-6">
						Token Refresh Job
					</CardTitle>
					<CardDescription className="text-sm leading-6 text-muted-foreground">
						No job runs yet
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p className="text-xs leading-5 text-muted-foreground">
						The automatic token refresh job runs every 15 minutes.
					</p>
				</CardContent>
			</Card>
		);
	}

	const timestamp = jobStatus.updated_at;
	const parsedTime = timestamp ? new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(timestamp) ? timestamp : `${timestamp}Z`) : null;
	const runTime = parsedTime && !Number.isNaN(parsedTime.getTime()) ? parsedTime : null;
	const relativeTime = runTime ? formatDistanceToNow(runTime, { addSuffix: true }) : "Unknown time";

	// Check if this is an error result (job itself failed, not individual connection failures)
	const isError = jobStatus.error != null;
	const hasFailures = jobStatus.refresh_failed > 0;
	const isSuccess = !isError && !hasFailures;

	if (isError) {
		return (
			<Card className={cn("overflow-hidden rounded-[var(--bf-radius-surface)] border-border/70 bg-card shadow-sm", className)}>
				<CardHeader className="pb-3">
					<div className="flex items-start justify-between gap-3">
						<CardTitle className="text-sm font-medium leading-6">
							Token Refresh Job
						</CardTitle>
						<Badge variant="destructive" className="rounded-[var(--bf-radius-control)] text-xs">
							Error
						</Badge>
					</div>
					<CardDescription className="text-sm leading-6 text-muted-foreground">
						{relativeTime}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="flex items-start gap-2 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-3 text-sm leading-6 text-[var(--bf-danger)]">
						<XCircle className="mt-0.5 h-4 w-4 shrink-0" />
						<span className="text-xs leading-5 [overflow-wrap:anywhere]">
							{jobStatus.error}
						</span>
					</div>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card className={cn("overflow-hidden rounded-[var(--bf-radius-surface)] border-border/70 bg-card shadow-sm", className)}>
			<CardHeader className="pb-3">
				<div className="flex items-start justify-between gap-3">
					<CardTitle className="text-sm font-medium leading-6">
						Token Refresh Job
					</CardTitle>
					<Badge
						variant={hasFailures ? "destructive" : "outline"}
						className={cn(
							"rounded-[var(--bf-radius-control)] text-xs",
							isSuccess &&
								"border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)]/60 text-[var(--bf-success)]",
						)}
					>
						{isSuccess ? (
							<>
								<CheckCircle2 className="mr-1 h-3.5 w-3.5" />
								OK
							</>
						) : (
							<>
								<AlertCircle className="mr-1 h-3.5 w-3.5" />
								{jobStatus.refresh_failed} Failed
							</>
						)}
					</Badge>
				</div>
				<CardDescription className="text-sm leading-6 text-muted-foreground">
					{relativeTime}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{isReadError && <div role="alert" className="space-y-2 text-sm"><p>Could not update status. Showing the last available run.</p><Button variant="outline" className="min-h-11" disabled={isFetching} onClick={() => void refetch()}>{isFetching ? "Retrying..." : "Retry"}</Button></div>}
				{/* Summary Stats */}
				<div className="flex flex-wrap items-center gap-3 text-sm">
					<div>
						<span className="text-muted-foreground">Total: </span>
						<span className="font-medium">
							{jobStatus.total_connections}
						</span>
					</div>
					{jobStatus.refreshed_successfully > 0 && (
						<div>
							<span className="text-muted-foreground">
								Refreshed:{" "}
							</span>
							<span className="font-medium text-[var(--bf-success)]">
								{jobStatus.refreshed_successfully}
							</span>
						</div>
					)}
				</div>

				{/* View Details Button */}
				<Dialog>
					<DialogTrigger asChild>
						<Button
							variant="ghost"
							className="min-h-11 w-full text-xs"
						>
							<FileText className="mr-2 h-4 w-4" />
							View Logs
						</Button>
					</DialogTrigger>
					<DialogContent className="w-[min(52rem,calc(100vw-1rem))] max-w-none rounded-[var(--bf-radius-surface)] p-0">
						<div className="max-h-[calc(100dvh-1rem)] overflow-y-auto px-4 py-4 sm:px-6">
							<DialogHeader>
								<DialogTitle className="text-base font-semibold sm:text-lg">
									Token Refresh Job Logs
								</DialogTitle>
								<DialogDescription className="text-sm leading-6 text-muted-foreground">
									Last run:{" "}
									{runTime ? runTime.toLocaleString() : "Unknown time"}
								</DialogDescription>
							</DialogHeader>

							<div className="mt-4 space-y-4">
							{/* Summary */}
							<div>
								<h4 className="mb-2 font-semibold leading-6">
									Summary
								</h4>
								<p className="text-sm leading-6 text-muted-foreground">
									Found {jobStatus.total_connections}{" "}
									connection
									{jobStatus.total_connections !== 1
										? "s"
										: ""}
									.
											{jobStatus.needs_refresh > 0 ? (
												<>
													{" "}
													{jobStatus.needs_refresh} needed
													refresh.
													{jobStatus.refreshed_successfully >
												0 && (
												<span className="text-[var(--bf-success)]">
													{" "}
													Refreshed{" "}
													{
														jobStatus.refreshed_successfully
													}{" "}
													successfully.
												</span>
											)}
											{jobStatus.refresh_failed > 0 && (
												<span className="text-[var(--bf-danger)]">
													{" "}
													Failed to refresh{" "}
													{jobStatus.refresh_failed}.
												</span>
											)}
										</>
									) : (
										" All tokens are up to date."
									)}
								</p>
							</div>

							{/* Errors */}
							{hasFailures &&
								jobStatus.errors &&
								jobStatus.errors.length > 0 && (
									<div>
										<h4 className="mb-2 flex items-center gap-2 font-semibold leading-6">
											<XCircle className="h-4 w-4 text-[var(--bf-danger)]" />
											Errors ({jobStatus.errors.length})
										</h4>
										<div className="space-y-3">
											{jobStatus.errors.map(
												(error, index) => (
													<div
														key={index}
														className="rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-3"
													>
														<div className="flex items-start gap-2">
															<div className="flex-1">
																<p className="text-sm leading-6 text-[var(--bf-danger)] [overflow-wrap:anywhere]">
																	{typeof error === "string"
																		? error
																		: JSON.stringify(error)}
																</p>
															</div>
														</div>
													</div>
												),
											)}
										</div>
									</div>
									)}

							{/* Success Message */}
							{!hasFailures && jobStatus.needs_refresh > 0 && (
								<div className="rounded-[var(--bf-radius-surface)] border border-[var(--bf-success)]/20 bg-[var(--bf-success-soft)]/60 p-4">
									<div className="flex items-center gap-2">
										<CheckCircle2 className="h-5 w-5 text-[var(--bf-success)]" />
										<p className="text-sm font-medium leading-6 text-[var(--bf-success)]">
											All tokens refreshed successfully!
										</p>
									</div>
								</div>
							)}
						</div>
						</div>
					</DialogContent>
				</Dialog>
			</CardContent>
		</Card>
	);
}
