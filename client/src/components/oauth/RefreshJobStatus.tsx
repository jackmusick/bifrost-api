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
import { Clock, CheckCircle2, XCircle, FileText } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface RefreshJobStatusProps {
	className?: string;
}

export function RefreshJobStatus({ className }: RefreshJobStatusProps) {
	const { data: jobStatus, isLoading } = useOAuthRefreshJobStatus();

	if (isLoading) {
		return (
			<Card className={className}>
				<CardHeader className="pb-3">
					<CardTitle className="text-sm font-medium">
						Token Refresh Job
					</CardTitle>
					<CardDescription>Loading status...</CardDescription>
				</CardHeader>
			</Card>
		);
	}

	if (!jobStatus) {
		return (
			<Card className={className}>
				<CardHeader className="pb-3">
					<CardTitle className="text-sm font-medium">
						Token Refresh Job
					</CardTitle>
					<CardDescription>No job runs yet</CardDescription>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">
						The automatic token refresh job runs every 15 minutes to
						keep OAuth tokens up to date.
					</p>
				</CardContent>
			</Card>
		);
	}

	// Check if this is an error result (job itself failed, not individual connection failures)
	const isError = jobStatus.error != null;

	if (isError) {
		return (
			<Card className={className}>
				<CardHeader className="pb-3">
					<div className="flex items-center justify-between">
						<div>
							<CardTitle className="text-sm font-medium">
								Token Refresh Job
							</CardTitle>
							<CardDescription className="flex items-center gap-2 mt-1">
								<Clock className="h-3 w-3" />
								<span>
									Last run:{" "}
									{formatDistanceToNow(
										new Date(jobStatus.updated_at),
										{ addSuffix: true },
									)}
								</span>
							</CardDescription>
						</div>
						<Badge variant="destructive">Error</Badge>
					</div>
				</CardHeader>
				<CardContent>
					<div className="flex items-start gap-2 text-sm">
						<XCircle className="h-4 w-4 text-destructive mt-0.5" />
						<div>
							<p className="font-medium">Job failed</p>
							<p className="text-muted-foreground">
								{jobStatus.error}
							</p>
						</div>
					</div>
				</CardContent>
			</Card>
		);
	}

	const successRate =
		jobStatus.needs_refresh > 0
			? Math.round(
					(jobStatus.refreshed_successfully /
						jobStatus.needs_refresh) *
						100,
				)
			: 100;

	const hasErrors = jobStatus.refresh_failed > 0;

	return (
		<Card className={className}>
			<CardHeader className="pb-2">
				<CardTitle className="text-sm font-medium">
					Token Refresh Job
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-3">
				{/* Status and Time */}
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2 text-xs text-muted-foreground">
						<Clock className="h-3 w-3" />
						<span>
							{formatDistanceToNow(
								new Date(jobStatus.updated_at + "Z"),
								{ addSuffix: true },
							)}
						</span>
					</div>
					<Badge
						variant={hasErrors ? "destructive" : "default"}
						className="text-xs"
					>
						{successRate}% Success
					</Badge>
				</div>

				{/* Summary Stats */}
				<div className="flex items-center justify-between text-sm">
					<div className="flex items-center gap-1.5">
						<span className="text-muted-foreground">Total:</span>
						<span className="font-semibold">
							{jobStatus.total_connections}
						</span>
					</div>
					{jobStatus.needs_refresh > 0 && (
						<div className="flex items-center gap-1.5">
							<span className="text-muted-foreground">
								Refreshed:
							</span>
							<span className="font-semibold text-green-600">
								{jobStatus.refreshed_successfully}
							</span>
						</div>
					)}
					{hasErrors && (
						<div className="flex items-center gap-1.5">
							<span className="text-muted-foreground">
								Failed:
							</span>
							<span className="font-semibold text-destructive">
								{jobStatus.refresh_failed}
							</span>
						</div>
					)}
				</div>

				{/* View Details Button */}
				<Dialog>
					<DialogTrigger asChild>
						<Button
							variant="ghost"
							size="sm"
							className="w-full h-8 text-xs"
						>
							<FileText className="mr-2 h-3 w-3" />
							View Logs
						</Button>
					</DialogTrigger>
					<DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
						<DialogHeader>
							<DialogTitle>Token Refresh Job Logs</DialogTitle>
							<DialogDescription>
								Last run:{" "}
								{new Date(
									jobStatus.updated_at + "Z",
								).toLocaleString()}
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 mt-4">
							{/* Summary */}
							<div>
								<h4 className="font-semibold mb-2">Summary</h4>
								<p className="text-sm text-muted-foreground">
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
												<span className="text-green-600">
													{" "}
													Refreshed{" "}
													{
														jobStatus.refreshed_successfully
													}{" "}
													successfully.
												</span>
											)}
											{jobStatus.refresh_failed > 0 && (
												<span className="text-destructive">
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
							{hasErrors &&
								jobStatus.errors &&
								jobStatus.errors.length > 0 && (
									<div>
										<h4 className="font-semibold mb-2 flex items-center gap-2">
											<XCircle className="h-4 w-4 text-destructive" />
											Errors ({jobStatus.errors.length})
										</h4>
										<div className="space-y-3">
											{jobStatus.errors.map(
												(
													error: {
														message: string;
														details?: string;
														connection_name?: string;
														org_id?: string;
														error?: string;
													},
													index: number,
												) => (
													<div
														key={index}
														className="border border-destructive/20 bg-destructive/5 rounded-lg p-3"
													>
														<div className="flex items-start gap-2">
															<div className="flex-1">
																<p className="font-medium text-sm">
																	{
																		error.connection_name
																	}
																	{error.org_id &&
																		error.org_id !==
																			"GLOBAL" && (
																			<span className="text-muted-foreground ml-2">
																				(
																				{
																					error.org_id
																				}

																				)
																			</span>
																		)}
																</p>
																<p className="text-sm text-muted-foreground mt-1">
																	{
																		error.error
																	}
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
							{!hasErrors && jobStatus.needs_refresh > 0 && (
								<div className="border border-green-200 bg-green-50 rounded-lg p-4">
									<div className="flex items-center gap-2">
										<CheckCircle2 className="h-5 w-5 text-green-600" />
										<p className="text-sm font-medium text-green-900">
											All tokens refreshed successfully!
										</p>
									</div>
								</div>
							)}
						</div>
					</DialogContent>
				</Dialog>
			</CardContent>
		</Card>
	);
}
