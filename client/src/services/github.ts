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
export type GitStatusResponse = components["schemas"]["GitRefreshStatusResponse"];
export type PullRequest = components["schemas"]["PullFromGitHubRequest"];
export type PushRequest = components["schemas"]["PushToGitHubRequest"];
export type FileChange = components["schemas"]["FileChange"];
export type CommitInfo = components["schemas"]["CommitInfo"];

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
	 * Initialize Git repository with remote
	 */
	async initRepo(
		config: GitHubConnectRequest,
	): Promise<GitStatusResponse> {
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
	 * Get commit history
	 */
	async getCommits(
		limit: number = 20,
		offset: number = 0,
	): Promise<{
		isGitRepo: boolean;
		commits: CommitInfo[];
	}> {
		const response = await authFetch(
			`/api/github/commits?limit=${limit}&offset=${offset}`,
		);

		if (!response.ok) {
			throw new Error("Failed to get commit history");
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
