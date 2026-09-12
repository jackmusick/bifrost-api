import { GitHubTokenField } from "./GitHubTokenField";
import { GitHubResourceSelect } from "./GitHubResourceSelect";
import { GitHubCreateRepositoryDialog } from "./GitHubCreateRepositoryDialog";
import { GitHubDisconnectDialog } from "./GitHubDisconnectDialog";
import { SettingsReadError } from "./SettingsReadError";
import { GitHubConnectionSummary } from "./GitHubConnectionSummary";
import { useRef, useState } from "react";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
	Loader2,
	Plus,
} from "lucide-react";
import { Github } from "@/components/icons/GithubIcon";
import {
	useGitHubConfig,
	useGitHubRepositories,
	useConfigureGitHub,
	useCreateGitHubRepository,
	useDisconnectGitHub,
	validateGitHubToken,
	listGitHubBranches,
	type GitHubRepoInfo,
	type GitHubBranchInfo,
	type GitHubConfigResponse,
} from "@/hooks/useGitHub";

export function GitHub() {
	const headingRef = useRef<HTMLDivElement>(null);
	const branchRequest = useRef(0);
	const [branchError, setBranchError] = useState(false);
	const [disconnected, setDisconnected] = useState(false);
	const [config, setConfig] = useState<GitHubConfigResponse | null>(null);
	const [saving, setSaving] = useState(false);
	const [testingToken, setTestingToken] = useState(false);
	const [loadingBranches, setLoadingBranches] = useState(false);

	// Form state
	const [token, setToken] = useState("");
	const [tokenValid, setTokenValid] = useState<boolean | null>(null);
	const [repositories, setRepositories] = useState<GitHubRepoInfo[]>([]);
	const [branches, setBranches] = useState<GitHubBranchInfo[]>([]);
	const [selectedRepo, setSelectedRepo] = useState<string>("");
	const [selectedBranch, setSelectedBranch] = useState<string>("main");

	// Create repo state
	const [showCreateRepo, setShowCreateRepo] = useState(false);
	const [newRepoName, setNewRepoName] = useState("");
	const [newRepoDescription, setNewRepoDescription] = useState("");
	const [newRepoPrivate, setNewRepoPrivate] = useState(true);
	const [creatingRepo, setCreatingRepo] = useState(false);

	// Disconnect confirmation state
	const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);

	// Load current GitHub configuration
	const { data: configData, isLoading: configLoading, isError: configError, isFetching: configFetching, refetch: refetchConfig } = useGitHubConfig();

	// Load repositories when token is saved but not configured
	const shouldLoadRepos = configData?.token_saved && !configData?.configured;
	const { data: reposData, isError: reposError, isFetching: reposFetching, refetch: refetchRepos } = useGitHubRepositories(shouldLoadRepos ?? false);

	// Mutations
	const configureMutation = useConfigureGitHub();
	const createRepoMutation = useCreateGitHubRepository();
	const disconnectMutation = useDisconnectGitHub();
	// Track the saved token for use in configuration
	const [savedToken, setSavedToken] = useState<string | null>(null);

	// Mirror server-loaded configData into local state so handlers can patch
	// it without going back through the query cache. Adjust during render
	// with a previous-value sentinel to avoid setState-in-effect.
	const [prevConfigDataRef, setPrevConfigDataRef] =
		useState<GitHubConfigResponse | undefined>(undefined);
	if (configData && prevConfigDataRef !== configData) {
		setPrevConfigDataRef(configData);
		setConfig(configData);
		if (configData.token_saved && !configData.configured) {
			setTokenValid(true);
		}
	}

	// Load repositories when they become available for an unconfigured token.
	const [prevReposDataRef, setPrevReposDataRef] =
		useState<typeof reposData | undefined>(undefined);
	if (
		reposData?.repositories &&
		config?.token_saved &&
		!config?.configured &&
		prevReposDataRef !== reposData
	) {
		setPrevReposDataRef(reposData);
		setRepositories(reposData.repositories);
	}

	// Validate token and load repositories
	const handleTokenValidation = async () => {
		if (testingToken || saving) return;
		if (!token.trim()) {
			toast.error("Please enter a GitHub Personal Access Token");
			return;
		}

		setTestingToken(true);
		setTokenValid(null);
		setRepositories([]);
		setBranches([]);

		try {
			const response = await validateGitHubToken(token);
			setRepositories(response.repositories);
			setSavedToken(token); // Save token for later use in configure
			setTokenValid(true);

			// Auto-select detected repo if available
			if (response.detected_repo) {
				await handleRepoSelection(response.detected_repo.full_name, response.detected_repo.branch);

				toast.success("Token validated successfully", {
					description: `Detected existing repository: ${response.detected_repo.full_name}`,
				});
			} else {
				toast.success("Token validated successfully", {
					description: `Found ${response.repositories.length} accessible repositories`,
				});
			}
		} catch {
			setTokenValid(false);
			toast.error("Invalid token", {
				description:
					"Please check your GitHub Personal Access Token and try again",
			});
		} finally {
			setTestingToken(false);
		}
	};

	// Load branches when repository is selected
	const handleRepoSelection = async (repoFullName: string, preferredBranch?: string) => {
		const request = ++branchRequest.current;
		setBranchError(false);
		setSelectedRepo(repoFullName);
		setBranches([]);
		setSelectedBranch(preferredBranch || "main");

		if (!repoFullName) return;

		setLoadingBranches(true);
		try {
			const branchList = await listGitHubBranches(repoFullName);
			if (request !== branchRequest.current) return;
			setBranches(branchList);

			// Auto-select main/master if available
			const defaultBranch =
				branchList.find((b) => b.name === preferredBranch) ||
				branchList.find((b) => b.name === "main") ||
				branchList.find((b) => b.name === "master");
			if (defaultBranch) {
				setSelectedBranch(defaultBranch.name);
			}
		} catch {
			if (request !== branchRequest.current) return;
			setBranchError(true);
		} finally {
			if (request === branchRequest.current) setLoadingBranches(false);
		}
	};

	// Create new repository
	const handleCreateRepository = async () => {
		if (creatingRepo) return;
		if (!newRepoName.trim()) {
			toast.error("Please enter a repository name");
			return;
		}

		setCreatingRepo(true);
		try {
			const newRepo = await createRepoMutation.mutateAsync({
				body: {
					name: newRepoName,
					description: newRepoDescription || null,
					private: newRepoPrivate,
					organization: null,
				},
			});

			toast.success("Repository created", {
				description: `Created ${newRepo.full_name}`,
			});

			// Update repositories list - refetch will happen automatically from mutation
			// For now, we manually update the state for immediate feedback
			setRepositories([
				...repositories,
				newRepo as unknown as GitHubRepoInfo,
			]);
			setSelectedRepo(newRepo.full_name);

			// Load branches for new repo
			await handleRepoSelection(newRepo.full_name);

			// Close dialog and reset form
			setShowCreateRepo(false);
			setNewRepoName("");
			setNewRepoDescription("");
			setNewRepoPrivate(true);
		} catch {
			// The dialog retains the draft and displays the mutation failure inline.
		} finally {
			setCreatingRepo(false);
		}
	};

	// Configure GitHub integration
	const handleConfigure = async () => {
		if (saving || testingToken || loadingBranches || branchError) return;
		// Token must be saved to configure
		if (!config?.token_saved && !savedToken) {
			toast.error("Please validate your token first");
			return;
		}

		if (!selectedRepo) {
			toast.error("Please select a repository");
			return;
		}

		// Proceed directly to configuration
		await handleSaveConfig();
	};

	// Save configuration (always replaces workspace with remote)
	const handleSaveConfig = async () => {
		setSaving(true);

		try {
			const setupResponse = await configureMutation.mutateAsync({
				body: {
					repo_url: selectedRepo,
					branch: selectedBranch,
				},
			});

			// Configuration is now async - show job queued message
			toast.success("GitHub configuration started", {
				description: `Job ${setupResponse.job_id} queued. Watch for notifications for progress.`,
			});
		} catch (error) {
			toast.error("Failed to save configuration", {
				description:
					error instanceof Error ? error.message : "Unknown error",
			});
		} finally {
			setSaving(false);
		}
	};

	// Disconnect GitHub integration
	const handleDisconnect = async () => {
		if (saving) return;
		setSaving(true);

		try {
			await disconnectMutation.mutateAsync({});
			setDisconnected(true);
			setShowDisconnectConfirm(false);
			setSavedToken(null);

			// Reset all state
			setConfig({
				configured: false,
				token_saved: false,
				repo_url: null,
				branch: null,
				backup_path: null,
			});
			setToken("");
			setTokenValid(null);
			setRepositories([]);
			setBranches([]);
			setSelectedRepo("");
			setSelectedBranch("main");

			toast.success("GitHub integration disconnected", {
				description: "Your credentials have been removed",
			});
		} catch (error) {
			toast.error("Failed to disconnect GitHub", {
				description:
					error instanceof Error ? error.message : "Unknown error",
			});
		} finally {
			setSaving(false);
		}
	};

	if (configLoading) {
		return (
			<div role="status" aria-label="Loading GitHub configuration" className="flex items-center justify-center py-12">
				<Loader2 className="h-8 w-8 animate-spin motion-reduce:animate-none text-muted-foreground" />
			</div>
		);
	}

	const readError = configError ? <SettingsReadError resource="GitHub configuration" cached={!!configData} pending={configFetching} onRetry={() => { void refetchConfig(); }} /> : null;
	if (!configData) return readError;

	return (
		<div className="space-y-6">
			{readError}
			<Card>
				<CardHeader>
					<div className="flex items-center gap-2">
						<Github className="h-5 w-5" />
						<CardTitle ref={headingRef} tabIndex={-1} className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">GitHub Integration</CardTitle>
					</div>
					<CardDescription>
						Connect your workspace to a GitHub repository for
						version control and collaboration
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Current Status */}
					{config?.configured ? (
						<GitHubConnectionSummary config={config} pending={saving} onDisconnect={() => { disconnectMutation.reset(); setDisconnected(false); setShowDisconnectConfirm(true); }} />
					) : (
						<>
							<GitHubTokenField value={token} saved={!!config?.token_saved} valid={tokenValid} pending={testingToken} disabled={saving} onChange={(value) => { setToken(value); setTokenValid(null); }} onValidate={() => { void handleTokenValidation(); }} />

							{/* Repository Selection - always show if token is valid or saved */}
							{(tokenValid || config?.token_saved) && (
								<div className="space-y-2">
									<div className="flex items-center justify-between gap-3">
										<Label htmlFor="repository">
											Repository
										</Label>
										<Button
											variant="ghost"
											size="sm"
											className="min-h-11"
											disabled={saving}
											onClick={() => { createRepoMutation.reset(); setShowCreateRepo(true); }}
										>
											<Plus className="h-4 w-4 mr-1" />
											Create New
										</Button>
									</div>
									<GitHubResourceSelect id="repository" value={selectedRepo} onChange={(value) => { void handleRepoSelection(value); }} placeholder={reposFetching && repositories.length === 0 ? "Loading repositories…" : "Select a repository"} disabled={saving || (repositories.length === 0 && (reposFetching || reposError))} options={repositories.map(repo => ({ value: repo.full_name, detail: repo.private ? "Private" : undefined }))} />
									{reposError && <SettingsReadError resource="GitHub repositories" cached={repositories.length > 0} pending={reposFetching} onRetry={() => { void refetchRepos(); }} />}
									{!reposError && !reposFetching && repositories.length === 0 && <p className="text-sm text-muted-foreground">No repositories available. Create one or check the saved token’s repository access.</p>}
								</div>
							)}

							{/* Branch Selection - always show if repo selected */}
							{(tokenValid || config?.token_saved) && (
								<div className="space-y-2">
									<Label htmlFor="branch">Branch</Label>
									<GitHubResourceSelect id="branch" value={selectedBranch} onChange={setSelectedBranch} placeholder="Select a branch" loading={loadingBranches} disabled={!selectedRepo || branchError || saving} options={branches.map(branch => ({ value: branch.name, detail: branch.protected ? "Protected" : undefined }))} />
									{branchError && <SettingsReadError resource="repository branches" cached={false} pending={loadingBranches} onRetry={() => { void handleRepoSelection(selectedRepo, selectedBranch); }} />}
									{!selectedRepo && (
										<p className="text-xs text-muted-foreground">
											Select a repository first
										</p>
									)}
								</div>
							)}

							{configureMutation.isError && <p role="alert" className="text-sm text-destructive">Could not start GitHub configuration. Your repository and branch selections are still here. Try again.</p>}
							{configureMutation.isSuccess && <p role="status" className="text-sm text-muted-foreground">Configuration queued. Follow its progress in notifications.</p>}

							{/* Save Button */}
							<div className="flex justify-end">
								<Button
									onClick={handleConfigure}
									className="min-h-11 w-full sm:w-auto"
									disabled={
										saving || testingToken || loadingBranches || branchError ||
										!selectedRepo ||
										(!config?.token_saved &&
											!token.trim()) ||
										(!config?.token_saved &&
											tokenValid !== true)
									}
								>
									{saving ? (
										<>
											<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
											Configuring...
										</>
									) : (
										<>
											<Github className="h-4 w-4 mr-2" />
											Configure GitHub
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

			<GitHubCreateRepositoryDialog open={showCreateRepo} name={newRepoName} description={newRepoDescription} isPrivate={newRepoPrivate} pending={creatingRepo} failed={createRepoMutation.isError} onClose={() => setShowCreateRepo(false)} onConfirm={() => { void handleCreateRepository(); }} onNameChange={setNewRepoName} onDescriptionChange={setNewRepoDescription} onPrivateChange={setNewRepoPrivate} />

			<GitHubDisconnectDialog open={showDisconnectConfirm} pending={saving} failed={disconnectMutation.isError} completed={disconnected} returnFocusRef={headingRef} onClose={() => setShowDisconnectConfirm(false)} onConfirm={() => { void handleDisconnect(); }} />
		</div>
	);
}
