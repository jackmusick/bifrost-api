/**
 * GitHub Integration API service
 *
 * Types are auto-generated from OpenAPI spec via `npm run generate:types`
 *
 * NOTE: This is a stub implementation matching the backend GitHub router.
 * Full Git integration features are not yet implemented in the Docker deployment.
 */

import type { components } from "@/lib/v1";

// Re-export types for convenience
export type GitHubConnectRequest = components["schemas"]["GitHubConnectRequest"];
export type GitStatusResponse = components["schemas"]["GitStatusResponse"];
export type PullRequest = components["schemas"]["PullRequest"];
export type PushRequest = components["schemas"]["PushRequest"];
export type CommitRequest = components["schemas"]["CommitRequest"];

// Additional types for UI components (not in backend yet)
// These will be replaced with generated types when Git integration is fully implemented
export interface FileChange {
	path: string;
	status: string;
	additions: number | null;
	deletions: number | null;
}

export interface CommitInfo {
	sha: string;
	message: string;
	author: string;
	timestamp: string;
	is_pushed: boolean;
}

export const githubService = {
	/**
	 * Get current Git status
	 */
	async getStatus(): Promise<GitStatusResponse> {
		const response = await fetch("/api/github/status");

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
		const response = await fetch("/api/github/init", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
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
		const response = await fetch("/api/github/pull", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: request ? JSON.stringify(request) : undefined,
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
		const response = await fetch("/api/github/commit", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ message } as CommitRequest),
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
		const response = await fetch("/api/github/push", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: request ? JSON.stringify(request) : undefined,
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
		const response = await fetch("/api/github/changes");

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
		const response = await fetch(
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
		const response = await fetch("/api/github/conflicts");

		if (!response.ok) {
			throw new Error("Failed to get merge conflicts");
		}

		return response.json();
	},

	/**
	 * Abort current merge operation
	 */
	async abortMerge(): Promise<unknown> {
		const response = await fetch("/api/github/abort-merge", {
			method: "POST",
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.message || "Failed to abort merge");
		}

		return response.json();
	},
};
