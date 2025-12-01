/**
 * Auth Setup
 *
 * Shared authentication setup that tests can use to get a logged-in state.
 */

import { test as setup, expect } from "@playwright/test";

// Test user credentials - requires BIFROST_DEFAULT_USER_EMAIL and
// BIFROST_DEFAULT_USER_PASSWORD to be set in the test environment
const TEST_USER_EMAIL = "admin@localhost";
const TEST_USER_PASSWORD = "admin";

export const STORAGE_STATE = "e2e/.auth/user.json";

setup("authenticate", async ({ page }) => {
	// Go to login page
	await page.goto("/login");

	// Wait for the login form to be visible
	await expect(page.getByRole("heading", { name: "Bifrost" })).toBeVisible();

	// Fill in credentials
	await page.getByLabel("Email").fill(TEST_USER_EMAIL);
	await page.getByLabel("Password").fill(TEST_USER_PASSWORD);

	// Click sign in
	await page.getByRole("button", { name: "Sign In" }).click();

	// Wait for redirect to dashboard (authenticated)
	await page.waitForURL("/", { timeout: 10000 });

	// Verify we're logged in by checking for something only visible when authenticated
	await expect(page.locator("body")).not.toContainText("Sign In");

	// Save authentication state
	await page.context().storageState({ path: STORAGE_STATE });
});
