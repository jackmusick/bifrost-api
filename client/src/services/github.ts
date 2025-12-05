/**
 * GitHub Integration API service
 *
 * Types are auto-generated from OpenAPI spec via `npm run generate:types`
 */

import { authFetch } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// =============================================================================
// Types - Auto-generated from OpenAPI spec
// =============================================================================

export type GitHubConnectRequest = components["schemas"]["GitHubConfigRequest"];
export type GitHubConfigResponse =
	components["schemas"]["GitHubConfigResponse"];
export type GitHubRepoInfo = components["schemas"]["GitHubRepoInfo"];
export type GitHubBranchInfo = components["schemas"]["GitHubBranchInfo"];
export type WorkspaceAnalysisResponse =
	components["schemas"]["WorkspaceAnalysisResponse"];
export type CreateRepoRequest = components["schemas"]["CreateRepoRequest"];
export type CreateRepoResponse = components["schemas"]["CreateRepoResponse"];
export type GitStatusResponse =
	components["schemas"]["GitRefreshStatusResponse"];
export type PullRequest = components["schemas"]["PullFromGitHubRequest"];
export type PushRequest = components["schemas"]["PushToGitHubRequest"];
export type FileChange = components["schemas"]["FileChange"];
export type CommitInfo = components["schemas"]["CommitInfo"];
export type ConflictInfo = components["schemas"]["ConflictInfo"];
export type CommitHistoryResponse =
	components["schemas"]["CommitHistoryResponse"];
export type DiscardCommitsResponse =
	components["schemas"]["DiscardUnpushedCommitsResponse"];

export const githubService = {
	/**
	 * Get current Git status
	 */
	async getStatus(): Promise<GitStatusResponse> {
		const response = await authFetch("/api/github/status");

		if (!response.ok) {
			throw new Error("Failed to get Git status");
		}

		return response.json();
	},

	/**
	 * Refresh Git status - uses GitHub API to get complete Git status
	 * Fast synchronous operation that returns status immediately
	 */
	async refreshStatus(): Promise<GitStatusResponse> {
		const response = await authFetch("/api/github/refresh", {
			method: "POST",
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to refresh Git status");
		}

		return response.json();
	},

	/**
	 * Get current GitHub configuration
	 */
	async getConfig(): Promise<components["schemas"]["GitHubConfigResponse"]> {
		const response = await authFetch("/api/github/config");

		if (!response.ok) {
			throw new Error("Failed to get GitHub configuration");
		}

		return response.json();
	},

	/**
	 * Validate GitHub token and list repositories
	 */
	async validate(
		token: string,
	): Promise<components["schemas"]["GitHubReposResponse"]> {
		const response = await authFetch("/api/github/validate", {
			method: "POST",
			body: JSON.stringify({ token }),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to validate token");
		}

		return response.json();
	},

	/**
	 * Configure GitHub integration
	 */
	async configure(config: {
		repo_url: string;
		branch: string;
	}): Promise<components["schemas"]["GitHubConfigResponse"]> {
		const response = await authFetch("/api/github/configure", {
			method: "POST",
			body: JSON.stringify(config),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to configure GitHub");
		}

		return response.json();
	},

	/**
	 * List repositories accessible with saved token
	 */
	async listRepositories(): Promise<
		components["schemas"]["GitHubRepoInfo"][]
	> {
		const response = await authFetch("/api/github/repositories");

		if (!response.ok) {
			throw new Error("Failed to list repositories");
		}

		const data = await response.json();
		return data.repositories;
	},

	/**
	 * List branches for a repository
	 */
	async listBranches(
		repoFullName: string,
	): Promise<components["schemas"]["GitHubBranchInfo"][]> {
		const response = await authFetch(
			`/api/github/branches?repo=${encodeURIComponent(repoFullName)}`,
		);

		if (!response.ok) {
			throw new Error("Failed to list branches");
		}

		const data = await response.json();
		return data.branches;
	},

	/**
	 * Analyze workspace before configuration
	 */
	async analyzeWorkspace(config: {
		repo_url: string;
		branch: string;
	}): Promise<components["schemas"]["WorkspaceAnalysisResponse"]> {
		const response = await authFetch("/api/github/analyze-workspace", {
			method: "POST",
			body: JSON.stringify(config),
		});

		if (!response.ok) {
			throw new Error("Failed to analyze workspace");
		}

		return response.json();
	},

	/**
	 * Create a new GitHub repository
	 */
	async createRepository(request: {
		name: string;
		description: string | null;
		private: boolean;
		organization: string | null;
	}): Promise<components["schemas"]["CreateRepoResponse"]> {
		const response = await authFetch("/api/github/create-repository", {
			method: "POST",
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to create repository");
		}

		return response.json();
	},

	/**
	 * Disconnect GitHub integration
	 */
	async disconnect(): Promise<void> {
		const response = await authFetch("/api/github/disconnect", {
			method: "POST",
		});

		if (!response.ok) {
			throw new Error("Failed to disconnect GitHub");
		}
	},

	/**
	 * Initialize Git repository with remote
	 */
	async initRepo(config: GitHubConnectRequest): Promise<GitStatusResponse> {
		const response = await authFetch("/api/github/init", {
			method: "POST",
			body: JSON.stringify(config),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to initialize repository");
		}

		return response.json();
	},

	/**
	 * Pull changes from remote repository
	 */
	async pull(request?: PullRequest): Promise<unknown> {
		const response = await authFetch("/api/github/pull", {
			method: "POST",
			...(request ? { body: JSON.stringify(request) } : {}),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to pull from remote");
		}

		return response.json();
	},

	/**
	 * Commit local changes
	 */
	async commit(message: string): Promise<unknown> {
		const response = await authFetch("/api/github/commit", {
			method: "POST",
			body: JSON.stringify({ message }),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to commit changes");
		}

		return response.json();
	},

	/**
	 * Push committed changes to remote repository
	 */
	async push(request?: PushRequest): Promise<unknown> {
		const response = await authFetch("/api/github/push", {
			method: "POST",
			...(request ? { body: JSON.stringify(request) } : {}),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to push to remote");
		}

		return response.json();
	},

	/**
	 * Get list of local changes
	 */
	async getChanges(): Promise<{
		isGitRepo: boolean;
		changes: FileChange[];
		totalChanges: number;
	}> {
		const response = await authFetch("/api/github/changes");

		if (!response.ok) {
			throw new Error("Failed to get local changes");
		}

		return response.json();
	},

	/**
	 * Get commit history with pagination
	 */
	async getCommits(
		limit: number = 20,
		offset: number = 0,
	): Promise<CommitHistoryResponse> {
		const response = await authFetch(
			`/api/github/commits?limit=${limit}&offset=${offset}`,
		);

		if (!response.ok) {
			throw new Error("Failed to get commit history");
		}

		return response.json();
	},

	/**
	 * Discard all unpushed commits
	 */
	async discardUnpushed(): Promise<DiscardCommitsResponse> {
		const response = await authFetch("/api/github/discard-unpushed", {
			method: "POST",
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(
				error.message || "Failed to discard unpushed commits",
			);
		}

		return response.json();
	},

	/**
	 * Discard a specific commit and all newer commits
	 */
	async discardCommit(commitSha: string): Promise<DiscardCommitsResponse> {
		const response = await authFetch("/api/github/discard-commit", {
			method: "POST",
			body: JSON.stringify({ commit_sha: commitSha }),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to discard commit");
		}

		return response.json();
	},

	/**
	 * Get merge conflicts
	 */
	async getConflicts(): Promise<{
		isGitRepo: boolean;
		conflicts: unknown[];
		totalConflicts: number;
	}> {
		const response = await authFetch("/api/github/conflicts");

		if (!response.ok) {
			throw new Error("Failed to get merge conflicts");
		}

		return response.json();
	},

	/**
	 * Abort current merge operation
	 */
	async abortMerge(): Promise<unknown> {
		const response = await authFetch("/api/github/abort-merge", {
			method: "POST",
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to abort merge");
		}

		return response.json();
	},
};
