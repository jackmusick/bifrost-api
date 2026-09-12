import { test, expect } from "@playwright/test";

type GitHubConfig = {
	configured: boolean;
	token_saved: boolean;
	repo_url: string | null;
	branch: string | null;
	backup_path: string | null;
};

const REPO = "fixture-owner/settings-acceptance";
const CREATED_REPO = "fixture-owner/settings-created";
const BRANCH = "release/settings-acceptance";

function unconfiguredConfig(): GitHubConfig {
	return {
		configured: false,
		token_saved: false,
		repo_url: null,
		branch: null,
		backup_path: null,
	};
}

test.describe("GitHub settings acceptance (admin)", () => {
	test("validates, selects, saves, reloads, creates a repo, and disconnects through the UI", async ({
		page,
	}) => {
		let config = unconfiguredConfig();
		let validateCalls = 0;
		let configurePayload: unknown;
		let disconnectCalls = 0;
		const repositories = [
			{ full_name: REPO, private: true },
			{ full_name: "fixture-owner/secondary", private: false },
		];

		await page.route("**/api/github/config", async (route) => {
			await route.fulfill({ json: config });
		});
		await page.route("**/api/github/validate", async (route) => {
			validateCalls += 1;
			await route.fulfill({
				json: {
					repositories,
					detected_repo: null,
				},
			});
		});
		await page.route("**/api/github/branches?**", async (route) => {
			const url = new URL(route.request().url());
			const repo = url.searchParams.get("repo");
			expect([REPO, CREATED_REPO]).toContain(repo);
			await route.fulfill({
				json: {
					branches:
						repo === CREATED_REPO
							? [{ name: "main", protected: false }]
							: [
									{ name: "main", protected: true },
									{ name: BRANCH, protected: false },
								],
				},
			});
		});
		await page.route("**/api/github/create-repository", async (route) => {
			const payload = route.request().postDataJSON() as {
				name: string;
				description: string | null;
				private: boolean;
				organization: string | null;
			};
			expect(payload).toMatchObject({
				name: "settings-created",
				description: "Created from settings acceptance",
				private: true,
				organization: null,
			});
			await route.fulfill({
				json: {
					full_name: CREATED_REPO,
					private: true,
				},
			});
		});
		await page.route("**/api/github/configure", async (route) => {
			configurePayload = route.request().postDataJSON();
			config = {
				configured: true,
				token_saved: true,
				repo_url: REPO,
				branch: BRANCH,
				backup_path: null,
			};
			await route.fulfill({
				json: { job_id: "github-settings-job", status: "queued" },
			});
		});
		await page.route("**/api/github/disconnect", async (route) => {
			disconnectCalls += 1;
			config = unconfiguredConfig();
			await route.fulfill({ json: { success: true } });
		});

		await page.goto("/settings/github");
		await expect(
			page.getByText("GitHub Integration", { exact: true }),
		).toBeVisible();

		await page
			.getByLabel("GitHub Personal Access Token")
			.fill("ghp_fixture_token");
		await page.getByRole("button", { name: "Validate" }).click();
		await expect(
			page.getByRole("status").filter({ hasText: "Token validated." }),
		).toBeVisible();
		expect(validateCalls).toBe(1);

		await page.getByRole("combobox", { name: /repository/i }).click();
		await page
			.getByRole("option", {
				name: /fixture-owner\/settings-acceptance/i,
			})
			.click();
		await page.getByRole("combobox", { name: /branch/i }).click();
		await page
			.getByRole("option", { name: /release\/settings-acceptance/i })
			.click();

		await page.getByRole("button", { name: "Create New" }).click();
		await page.getByLabel("Repository Name").fill("settings-created");
		await page
			.getByLabel("Description (Optional)")
			.fill("Created from settings acceptance");
		await page.getByRole("button", { name: "Create Repository" }).click();
		await expect(page.getByRole("dialog")).not.toBeVisible();

		await page.getByRole("combobox", { name: /repository/i }).click();
		await page
			.getByRole("option", {
				name: /fixture-owner\/settings-acceptance/i,
			})
			.click();
		await page.getByRole("combobox", { name: /branch/i }).click();
		await page
			.getByRole("option", { name: /release\/settings-acceptance/i })
			.click();
		await page.getByRole("button", { name: "Configure GitHub" }).click();

		expect(configurePayload).toEqual({ repo_url: REPO, branch: BRANCH });
		await expect(page.getByRole("region", { name: "Connected GitHub repository" })).toBeVisible();

		await page.reload();
		const summary = page.getByRole("region", {
			name: "Connected GitHub repository",
		});
		await expect(summary).toContainText("Connected");
		await expect(summary).toContainText(REPO);
		await expect(summary).toContainText(BRANCH);

		await summary.getByRole("button", { name: "Disconnect" }).click();
		await expect(
			page.getByRole("dialog", { name: "Disconnect GitHub Integration" }),
		).toBeVisible();
		await page
			.getByRole("dialog", { name: "Disconnect GitHub Integration" })
			.getByRole("button", { name: "Disconnect" })
			.click();
		expect(disconnectCalls).toBe(1);
		await expect(
			page.getByLabel("GitHub Personal Access Token"),
		).toBeVisible();
	});
});
