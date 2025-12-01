import { AlertCircle, RefreshCw, Terminal, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/hooks/useAuth";
import { useWorkflowEngineHealth } from "@/hooks/useWorkflowEngineHealth";

export function WorkflowEngineError() {
	const { isPlatformAdmin } = useAuth();
	const { refetch, isRefetching } = useWorkflowEngineHealth();

	const handleRetry = async () => {
		await refetch();
	};

	return (
		<div className="min-h-screen flex items-center justify-center bg-background p-6">
			<Card className="max-w-2xl w-full">
				<CardHeader>
					<div className="flex items-center gap-3">
						<div className="p-3 rounded-full bg-destructive/10">
							<AlertCircle className="h-8 w-8 text-destructive" />
						</div>
						<div>
							<CardTitle className="text-2xl">
								Server Unavailable
							</CardTitle>
							<CardDescription>
								Unable to connect to the server
							</CardDescription>
						</div>
					</div>
				</CardHeader>
				<CardContent className="space-y-6">
					<Alert>
						<Terminal className="h-4 w-4" />
						<AlertTitle>Service Status</AlertTitle>
						<AlertDescription>
							The server is currently unavailable. Workflows,
							forms, and execution history cannot be accessed
							until the service is restored.
						</AlertDescription>
					</Alert>

					{isPlatformAdmin && (
						<Card>
							<CardHeader>
								<CardTitle className="text-lg">
									Need Help?
								</CardTitle>
								<CardDescription>
									View detailed troubleshooting instructions
								</CardDescription>
							</CardHeader>
							<CardContent>
								<Button
									variant="outline"
									onClick={() =>
										window.open(
											"/docs/troubleshooting/server-unavailable",
											"_blank",
										)
									}
									className="w-full"
								>
									<BookOpen className="mr-2 h-4 w-4" />
									View Troubleshooting Documentation
								</Button>
								<p className="text-sm text-muted-foreground mt-3">
									The documentation includes step-by-step
									instructions for both development and
									production environments.
								</p>
							</CardContent>
						</Card>
					)}

					{!isPlatformAdmin && (
						<Alert>
							<AlertCircle className="h-4 w-4" />
							<AlertTitle>Contact Administrator</AlertTitle>
							<AlertDescription>
								Please contact your platform administrator to
								resolve this issue. Workflows and forms will be
								unavailable until the server is restored.
							</AlertDescription>
						</Alert>
					)}

					<Button
						onClick={handleRetry}
						disabled={isRefetching}
						className="w-full"
					>
						<RefreshCw
							className={`mr-2 h-4 w-4 ${isRefetching ? "animate-spin" : ""}`}
						/>
						{isRefetching ? "Checking..." : "Retry Connection"}
					</Button>
				</CardContent>
			</Card>
		</div>
	);
}
