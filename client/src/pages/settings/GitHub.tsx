import { useState, useEffect } from "react";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { Loader2, Github, AlertCircle } from "lucide-react";
import { githubService, type GitStatusResponse } from "@/services/github";

/**
 * GitHub Settings Page
 *
 * NOTE: This is a stub UI matching the backend GitHub router stub.
 * Full Git integration features are not yet implemented in the Docker deployment.
 */
export function GitHub() {
	const [status, setStatus] = useState<GitStatusResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [connecting, setConnecting] = useState(false);

	// Form state
	const [repoUrl, setRepoUrl] = useState("");
	const [authToken, setAuthToken] = useState("");
	const [branch, setBranch] = useState("main");

	// Warning dialog state
	const [showNotImplementedDialog, setShowNotImplementedDialog] =
		useState(false);

	// Load current Git status
	useEffect(() => {
		async function loadStatus() {
			try {
				const data = await githubService.getStatus();
				setStatus(data);
			} catch (error) {
				console.error("Failed to load Git status:", error);
			} finally {
				setLoading(false);
			}
		}

		loadStatus();
	}, []);

	// Handle repository connection (will fail with 501 Not Implemented)
	const handleConnect = async () => {
		if (!repoUrl.trim()) {
			toast.error("Please enter a repository URL");
			return;
		}

		if (!authToken.trim()) {
			toast.error("Please enter a GitHub token");
			return;
		}

		setConnecting(true);
		try {
			await githubService.initRepo({
				repo_url: repoUrl,
				auth_token: authToken,
				branch,
			});

			// If it succeeds (unlikely with stub), refresh status
			const updatedStatus = await githubService.getStatus();
			setStatus(updatedStatus);

			toast.success("GitHub integration configured", {
				description: "Your workspace is now connected to GitHub",
			});

			// Clear form
			setRepoUrl("");
			setAuthToken("");
			setBranch("main");
		} catch (error) {
			// Expected: 501 Not Implemented
			if (
				error instanceof Error &&
				error.message.includes("not yet implemented")
			) {
				setShowNotImplementedDialog(true);
			} else {
				toast.error("Failed to connect repository", {
					description:
						error instanceof Error
							? error.message
							: "Unknown error",
				});
			}
		} finally {
			setConnecting(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<Card>
				<CardHeader>
					<div className="flex items-center gap-2">
						<Github className="h-5 w-5" />
						<CardTitle>GitHub Integration</CardTitle>
					</div>
					<CardDescription>
						Connect your workspace to a GitHub repository for
						version control and collaboration
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Current Status */}
					{status?.initialized ? (
						<div className="space-y-4">
							<div className="rounded-lg border bg-muted/50 p-4">
								<div className="space-y-1 text-sm text-muted-foreground">
									<div>
										<strong>Branch:</strong>{" "}
										{status.current_branch || "Unknown"}
									</div>
									<div>
										<strong>Changes:</strong>{" "}
										{status.changed_files?.length || 0}{" "}
										file(s)
									</div>
									<div>
										<strong>Commits ahead:</strong>{" "}
										{status.commits_ahead}
									</div>
									<div>
										<strong>Commits behind:</strong>{" "}
										{status.commits_behind}
									</div>
								</div>
							</div>
						</div>
					) : (
						<>
							{/* Repository URL */}
							<div className="space-y-2">
								<Label htmlFor="repository-url">
									Repository URL
								</Label>
								<Input
									id="repository-url"
									type="text"
									placeholder="https://github.com/username/repo.git"
									value={repoUrl}
									onChange={(e) => setRepoUrl(e.target.value)}
								/>
								<p className="text-xs text-muted-foreground">
									Enter the full URL of your GitHub repository
								</p>
							</div>

							{/* GitHub Token */}
							<div className="space-y-2">
								<Label htmlFor="github-token">
									GitHub Personal Access Token
								</Label>
								<Input
									id="github-token"
									type="password"
									autoComplete="off"
									placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
									value={authToken}
									onChange={(e) =>
										setAuthToken(e.target.value)
									}
								/>
								<p className="text-xs text-muted-foreground">
									Create a token at{" "}
									<a
										href="https://github.com/settings/tokens/new"
										target="_blank"
										rel="noopener noreferrer"
										className="underline hover:text-foreground"
									>
										github.com/settings/tokens
									</a>{" "}
									with <code className="text-xs">repo</code>{" "}
									scope
								</p>
							</div>

							{/* Branch */}
							<div className="space-y-2">
								<Label htmlFor="branch">Branch</Label>
								<Input
									id="branch"
									type="text"
									placeholder="main"
									value={branch}
									onChange={(e) => setBranch(e.target.value)}
								/>
							</div>

							{/* Connect Button */}
							<div className="flex justify-end">
								<Button
									onClick={handleConnect}
									disabled={
										connecting ||
										!repoUrl.trim() ||
										!authToken.trim()
									}
								>
									{connecting ? (
										<>
											<Loader2 className="h-4 w-4 mr-2 animate-spin" />
											Connecting...
										</>
									) : (
										<>
											<Github className="h-4 w-4 mr-2" />
											Connect GitHub
										</>
									)}
								</Button>
							</div>
						</>
					)}
				</CardContent>
			</Card>

			{/* Additional Information */}
			<Card>
				<CardHeader>
					<CardTitle className="text-base">How it works</CardTitle>
				</CardHeader>
				<CardContent className="space-y-2 text-sm text-muted-foreground">
					<p>
						Once configured, your workspace will be synced with the
						selected GitHub repository:
					</p>
					<ul className="list-disc list-inside space-y-1 ml-2">
						<li>
							Use the <strong>Source Control</strong> panel in the
							Code Editor to view changes
						</li>
						<li>
							Commit and push changes directly from the editor
						</li>
						<li>
							Pull updates from GitHub to keep your workspace in
							sync
						</li>
						<li>Resolve merge conflicts with inline tools</li>
					</ul>
				</CardContent>
			</Card>

			{/* Not Implemented Dialog */}
			<Dialog
				open={showNotImplementedDialog}
				onOpenChange={setShowNotImplementedDialog}
			>
				<DialogContent className="max-w-md">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2 text-amber-600">
							<AlertCircle className="h-5 w-5" />
							Feature Not Yet Available
						</DialogTitle>
						<DialogDescription className="space-y-3">
							<p>
								Git integration is not yet implemented in the
								Docker deployment. This feature will be
								available in a future update.
							</p>
							<div className="rounded-lg bg-muted p-3 space-y-2 text-sm">
								<p className="font-medium text-foreground">
									Coming soon:
								</p>
								<ul className="list-disc list-inside space-y-1 ml-2">
									<li>Full Git repository integration</li>
									<li>Commit and push from the editor</li>
									<li>Pull updates from remote</li>
									<li>Conflict resolution tools</li>
								</ul>
							</div>
						</DialogDescription>
					</DialogHeader>

					<DialogFooter>
						<Button
							variant="outline"
							onClick={() => setShowNotImplementedDialog(false)}
						>
							Close
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
