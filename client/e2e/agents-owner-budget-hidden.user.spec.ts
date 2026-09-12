/**
 * Agent Settings — Budget Field Visibility (Non-Admin User)
 *
 * Server-gates the budget fields (max_iterations, max_token_budget,
 * llm_max_tokens) to platform admins (T19). The settings tab also visually
 * hides both the Budgets section AND the Organization selector for non-admins.
 * This spec runs under the org-user storage state and verifies neither
 * appears.
 *
 * `beforeAll` seeds a private agent owned by the member. An authenticated
 * agent owned by an admin may be runnable without being editable by the member.
 */

import { test, expect } from "./fixtures/api-fixture";

let seededAgentId: string | null = null;

test.describe("Agent Settings — Budget Visibility (non-admin user)", () => {
	test.beforeAll(async ({ api }) => {
		const response = await api.post("/api/agents", {
			data: {
				name: `Member budget visibility ${Date.now()}`,
				system_prompt: "Member-owned settings acceptance fixture.",
				channels: ["chat"],
				access_level: "private",
			},
		});
		expect(response.ok(), await response.text()).toBe(true);
		seededAgentId = (await response.json()).id;
	});

	test.afterAll(async ({ api }) => {
		if (seededAgentId) {
			const response = await api.delete(`/api/agents/${seededAgentId}`);
			expect([200, 204, 404]).toContain(response.status());
		}
	});

	test("budget fields are not visible to non-admin users", async ({
		page,
	}) => {
		expect(seededAgentId).not.toBeNull();

		await page.goto(`/agents/${seededAgentId}`);
		await page.getByRole("tab", { name: /settings/i }).click();
		await expect(
			page.getByRole("textbox", { name: /name/i }).first(),
		).toBeVisible({ timeout: 10000 });

		// Budget fields must not appear for non-admins.
		await expect(page.getByLabel(/max iterations/i)).toHaveCount(0);
		await expect(page.getByLabel(/max token budget/i)).toHaveCount(0);
		await expect(page.getByLabel(/max tokens \/ response/i)).toHaveCount(0);

		// Organization selector is also admin-only (see AgentSettingsTab).
		await expect(page.getByLabel(/^organization/i)).toHaveCount(0);

		await page.screenshot({
			path: "test-results/screenshots/agent-settings-no-budget.png",
			fullPage: true,
		});
	});
});
