import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";
import { GitHub } from "./GitHub";

const {
	mockUseGitHubConfig,
	mockUseGitHubRepositories,
	mockConfigureMutateAsync,
	mockCreateRepoMutateAsync,
	mockDisconnectMutateAsync,
	mockValidateGitHubToken,
	mockListGitHubBranches,
} = vi.hoisted(() => ({
	mockUseGitHubConfig: vi.fn(),
	mockUseGitHubRepositories: vi.fn(),
	mockConfigureMutateAsync: vi.fn(),
	mockCreateRepoMutateAsync: vi.fn(),
	mockDisconnectMutateAsync: vi.fn(),
	mockValidateGitHubToken: vi.fn(),
	mockListGitHubBranches: vi.fn(),
}));

vi.mock("@/hooks/useGitHub", () => ({
	useGitHubConfig: () => mockUseGitHubConfig(),
	useGitHubRepositories: (enabled?: boolean) =>
		mockUseGitHubRepositories(enabled),
	useConfigureGitHub: () => ({
		mutateAsync: mockConfigureMutateAsync,
		isError: false,
		isSuccess: false,
	}),
	useCreateGitHubRepository: () => ({
		mutateAsync: mockCreateRepoMutateAsync,
		isError: false,
		reset: vi.fn(),
	}),
	useDisconnectGitHub: () => ({
		mutateAsync: mockDisconnectMutateAsync,
		isError: false,
		reset: vi.fn(),
	}),
	validateGitHubToken: (...args: unknown[]) =>
		mockValidateGitHubToken(...args),
	listGitHubBranches: (...args: unknown[]) => mockListGitHubBranches(...args),
}));

beforeEach(() => {
	vi.clearAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
	mockUseGitHubConfig.mockReturnValue({
		data: {
			configured: false,
			token_saved: false,
			repo_url: null,
			branch: null,
			backup_path: null,
		},
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});
	mockUseGitHubRepositories.mockReturnValue({
		data: undefined,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});
	mockConfigureMutateAsync.mockResolvedValue({
		job_id: "job-1",
		status: "queued",
	});
	mockCreateRepoMutateAsync.mockResolvedValue({
		full_name: "fixture-owner/new-repo",
		private: true,
	});
	mockDisconnectMutateAsync.mockResolvedValue({ success: true });
	mockValidateGitHubToken.mockResolvedValue({
		repositories: [
			{ full_name: "fixture-owner/app", private: true },
			{ full_name: "fixture-owner/site", private: false },
		],
		detected_repo: null,
	});
	mockListGitHubBranches.mockResolvedValue([
		{ name: "main", protected: true },
		{ name: "preview", protected: false },
	]);
});

describe("GitHub settings", () => {
	it("validates a token, selects repository and branch, then submits the actual configure contract", async () => {
		const { user } = renderWithProviders(<GitHub />);

		await user.type(
			screen.getByLabelText("GitHub Personal Access Token"),
			"ghp_fixture_token",
		);
		await user.click(screen.getByRole("button", { name: "Validate" }));

		await waitFor(() =>
			expect(mockValidateGitHubToken).toHaveBeenCalledWith(
				"ghp_fixture_token",
			),
		);
		expect(await screen.findByText("Token validated.")).toBeVisible();

		await user.click(screen.getByRole("combobox", { name: /repository/i }));
		await user.click(
			await screen.findByRole("option", { name: /fixture-owner\/app/i }),
		);
		await waitFor(() =>
			expect(mockListGitHubBranches).toHaveBeenCalledWith(
				"fixture-owner/app",
			),
		);

		await user.click(screen.getByRole("combobox", { name: /branch/i }));
		await user.click(
			await screen.findByRole("option", { name: /^preview$/i }),
		);
		await user.click(
			screen.getByRole("button", { name: "Configure GitHub" }),
		);

		await waitFor(() =>
			expect(mockConfigureMutateAsync).toHaveBeenCalledWith({
				body: { repo_url: "fixture-owner/app", branch: "preview" },
			}),
		);
	});

	it("creates a repository with the current dialog draft and selects the created repo", async () => {
		const { user } = renderWithProviders(<GitHub />);

		await user.type(
			screen.getByLabelText("GitHub Personal Access Token"),
			"ghp_token",
		);
		await user.click(screen.getByRole("button", { name: "Validate" }));
		await screen.findByText("Token validated.");

		await user.click(screen.getByRole("button", { name: "Create New" }));
		const dialog = screen.getByRole("dialog", {
			name: "Create New Repository",
		});
		await user.type(
			within(dialog).getByLabelText("Repository Name"),
			"new-repo",
		);
		await user.type(
			within(dialog).getByLabelText("Description (Optional)"),
			"Repository from settings",
		);
		await user.click(
			within(dialog).getByRole("button", { name: "Create Repository" }),
		);

		await waitFor(() =>
			expect(mockCreateRepoMutateAsync).toHaveBeenCalledWith({
				body: {
					name: "new-repo",
					description: "Repository from settings",
					private: true,
					organization: null,
				},
			}),
		);
		await waitFor(() =>
			expect(mockListGitHubBranches).toHaveBeenCalledWith(
				"fixture-owner/new-repo",
			),
		);
	});

	it("shows configured repository summary and disconnects through confirmation", async () => {
		mockUseGitHubConfig.mockReturnValue({
			data: {
				configured: true,
				token_saved: true,
				repo_url: "fixture-owner/configured",
				branch: "main",
				backup_path: null,
			},
			isLoading: false,
			isError: false,
			isFetching: false,
			refetch: vi.fn(),
		});
		const { user } = renderWithProviders(<GitHub />);

		const summary = screen.getByRole("region", {
			name: "Connected GitHub repository",
		});
		expect(summary).toHaveTextContent("fixture-owner/configured");
		expect(summary).toHaveTextContent("main");

		await user.click(
			within(summary).getByRole("button", { name: "Disconnect" }),
		);
		const dialog = screen.getByRole("dialog", {
			name: "Disconnect GitHub Integration",
		});
		await user.click(
			within(dialog).getByRole("button", { name: "Disconnect" }),
		);

		await waitFor(() =>
			expect(mockDisconnectMutateAsync).toHaveBeenCalledWith({}),
		);
		expect(
			screen.getByLabelText("GitHub Personal Access Token"),
		).toBeVisible();
	});
});
