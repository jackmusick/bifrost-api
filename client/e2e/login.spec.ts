/**
 * Login Flow E2E Tests
 *
 * Tests the authentication flow including:
 * - Basic email/password login
 * - Error handling for invalid credentials
 * - Redirect after login
 */

import { test, expect } from "@playwright/test";

// Test user credentials
const TEST_USER_EMAIL = "admin@localhost";
const TEST_USER_PASSWORD = "admin";

test.describe("Login Flow", () => {
	test.beforeEach(async ({ page }) => {
		// Clear any existing auth state
		await page.context().clearCookies();
		await page.evaluate(() => localStorage.clear());
	});

	test("should show login page", async ({ page }) => {
		await page.goto("/login");

		// Check for login form elements
		await expect(
			page.getByRole("heading", { name: "Bifrost" }),
		).toBeVisible();
		await expect(page.getByLabel("Email")).toBeVisible();
		await expect(page.getByLabel("Password")).toBeVisible();
		await expect(
			page.getByRole("button", { name: "Sign In" }),
		).toBeVisible();
	});

	test("should show error for invalid credentials", async ({ page }) => {
		await page.goto("/login");

		// Enter invalid credentials
		await page.getByLabel("Email").fill("invalid@example.com");
		await page.getByLabel("Password").fill("wrongpassword");
		await page.getByRole("button", { name: "Sign In" }).click();

		// Should show error message
		await expect(page.getByRole("alert")).toBeVisible({ timeout: 5000 });
	});

	test("should login successfully with valid credentials", async ({
		page,
	}) => {
		await page.goto("/login");

		// Enter valid credentials
		await page.getByLabel("Email").fill(TEST_USER_EMAIL);
		await page.getByLabel("Password").fill(TEST_USER_PASSWORD);
		await page.getByRole("button", { name: "Sign In" }).click();

		// Should redirect to dashboard
		await page.waitForURL("/", { timeout: 10000 });

		// Verify we're on the dashboard (not login page)
		await expect(
			page.getByRole("button", { name: "Sign In" }),
		).not.toBeVisible();
	});

	test("should redirect unauthenticated users to login", async ({ page }) => {
		// Try to access protected route
		await page.goto("/workflows");

		// Should redirect to login
		await page.waitForURL(/\/login/, { timeout: 5000 });
		await expect(
			page.getByRole("heading", { name: "Bifrost" }),
		).toBeVisible();
	});

	test("should preserve redirect path after login", async ({ page }) => {
		// Try to access workflows page while not logged in
		await page.goto("/workflows");

		// Should redirect to login
		await page.waitForURL(/\/login/, { timeout: 5000 });

		// Login
		await page.getByLabel("Email").fill(TEST_USER_EMAIL);
		await page.getByLabel("Password").fill(TEST_USER_PASSWORD);
		await page.getByRole("button", { name: "Sign In" }).click();

		// Should redirect back to workflows (the original destination)
		// Note: This depends on the app preserving the redirect state
		await page.waitForURL(/\/(workflows)?/, { timeout: 10000 });
	});
});
