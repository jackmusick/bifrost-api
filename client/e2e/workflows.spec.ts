/**
 * Workflow Execution E2E Tests
 *
 * Tests the workflow execution flow including:
 * - Viewing workflows list
 * - Executing a workflow
 * - Viewing execution results with realtime updates
 */

import { test, expect } from "@playwright/test";

// Test user credentials
const TEST_USER_EMAIL = "admin@localhost";
const TEST_USER_PASSWORD = "admin";

// Helper to login before tests
async function login(page: import("@playwright/test").Page) {
	await page.goto("/login");
	await page.getByLabel("Email").fill(TEST_USER_EMAIL);
	await page.getByLabel("Password").fill(TEST_USER_PASSWORD);
	await page.getByRole("button", { name: "Sign In" }).click();
	await page.waitForURL("/", { timeout: 10000 });
}

test.describe("Workflows", () => {
	test.beforeEach(async ({ page }) => {
		// Clear auth state and login fresh
		await page.context().clearCookies();
		await page.evaluate(() => localStorage.clear());
		await login(page);
	});

	test("should display workflows page", async ({ page }) => {
		await page.goto("/workflows");

		// Wait for workflows page to load
		await expect(
			page.getByRole("heading", { name: /workflows/i }),
		).toBeVisible({ timeout: 10000 });

		// Either we have workflows or we have some content
		await expect(page.locator("main")).toBeVisible();
	});

	test("should navigate to workflow execution page", async ({ page }) => {
		await page.goto("/workflows");

		// Wait for page to load
		await expect(
			page.getByRole("heading", { name: /workflows/i }),
		).toBeVisible({ timeout: 10000 });

		// Look for an execute button
		const executeButton = page
			.getByRole("button", { name: /execute/i })
			.first();

		// Skip if no workflows available
		if (!(await executeButton.isVisible().catch(() => false))) {
			test.skip();
			return;
		}

		await executeButton.click();

		// Should be on execute workflow page
		await expect(page.getByText(/execute workflow/i)).toBeVisible({
			timeout: 5000,
		});
	});
});

test.describe("Execution History", () => {
	test.beforeEach(async ({ page }) => {
		await page.context().clearCookies();
		await page.evaluate(() => localStorage.clear());
		await login(page);
	});

	test("should display execution history page", async ({ page }) => {
		await page.goto("/history");

		// Wait for history page to load
		await expect(
			page.getByRole("heading", { name: /history/i }),
		).toBeVisible({
			timeout: 10000,
		});
	});

	test("should navigate to execution details", async ({ page }) => {
		await page.goto("/history");

		// Wait for page to load
		await expect(
			page.getByRole("heading", { name: /history/i }),
		).toBeVisible({
			timeout: 10000,
		});

		// Look for a clickable execution row
		const executionRow = page
			.locator("table tbody tr, [data-testid='execution-row']")
			.first();

		// Skip if no executions
		if (!(await executionRow.isVisible().catch(() => false))) {
			test.skip();
			return;
		}

		await executionRow.click();

		// Should navigate to execution details
		await page.waitForURL(/\/history\/[a-f0-9-]+/, { timeout: 5000 });
	});
});

test.describe("Workflow Execution with Realtime Results", () => {
	test.beforeEach(async ({ page }) => {
		await page.context().clearCookies();
		await page.evaluate(() => localStorage.clear());
		await login(page);
	});

	test("should execute workflow and see realtime status updates", async ({
		page,
	}) => {
		// Navigate to workflows
		await page.goto("/workflows");
		await expect(
			page.getByRole("heading", { name: /workflows/i }),
		).toBeVisible({ timeout: 10000 });

		// Find a simple test workflow to execute
		// Look for example_basic_workflow or test_workflow
		const workflowCard = page
			.locator(
				"text=example_basic_workflow, text=test_workflow, [data-workflow-name]",
			)
			.first();

		// Skip if no suitable workflow found
		if (!(await workflowCard.isVisible().catch(() => false))) {
			// Try to find any execute button
			const anyExecuteBtn = page
				.getByRole("button", { name: /execute/i })
				.first();
			if (!(await anyExecuteBtn.isVisible().catch(() => false))) {
				test.skip();
				return;
			}
			await anyExecuteBtn.click();
		} else {
			// Click on the workflow card or its execute button
			const executeBtn = workflowCard
				.locator('button:has-text("Execute"), [aria-label*="execute"]')
				.first();
			if (await executeBtn.isVisible().catch(() => false)) {
				await executeBtn.click();
			} else {
				await workflowCard.click();
			}
		}

		// Wait for execute workflow page
		await page
			.waitForURL(/\/workflows\/.*\/execute/, { timeout: 5000 })
			.catch(() => {
				// May already be on execute page or need different navigation
			});

		// Look for execute/run button on the form
		const runButton = page
			.getByRole("button", { name: /execute|run|submit/i })
			.first();

		if (await runButton.isVisible().catch(() => false)) {
			await runButton.click();

			// Should redirect to execution details page
			await page.waitForURL(/\/history\/[a-f0-9-]+/, { timeout: 15000 });

			// Should see execution status
			await expect(
				page.locator(
					"text=Pending, text=Running, text=Completed, text=Success, text=Failed",
				),
			).toBeVisible({ timeout: 30000 });

			// Wait for completion (up to 30 seconds for simple workflows)
			await expect(
				page.locator("text=Completed, text=Success, text=Failed"),
			).toBeVisible({ timeout: 30000 });
		}
	});
});

test.describe("Dashboard", () => {
	test.beforeEach(async ({ page }) => {
		await page.context().clearCookies();
		await page.evaluate(() => localStorage.clear());
		await login(page);
	});

	test("should display dashboard after login", async ({ page }) => {
		await page.goto("/");

		// Dashboard should be visible
		// Look for common dashboard elements
		await expect(page.locator("main")).toBeVisible({ timeout: 10000 });

		// Should not be on login page
		await expect(
			page.getByRole("button", { name: "Sign In" }),
		).not.toBeVisible();
	});
});
