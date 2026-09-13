/**
 * SDK Update UI Happy Path (Admin)
 *
 * Uses dev fixture route data to keep screenshots deterministic while still
 * rendering the real Applications page/components and overflow interaction.
 * No browser polling is mocked or used; the queued durable job response drives
 * the local "Updating SDK" state until platform-job WebSocket updates arrive.
 */

import { test, expect } from "./fixtures/api-fixture";
import type { Page } from "@playwright/test";

const NOW = "2026-09-12T12:00:00Z";

function app(overrides: Record<string, unknown>) {
	return {
		id: "11111111-1111-1111-1111-111111111111",
		name: "Dispatch Board",
		description: "Routes technician work.",
		icon: null,
		slug: "dispatch-board",
		organization_id: null,
		published_at: NOW,
		deployed_at: NOW,
		created_at: NOW,
		updated_at: NOW,
		created_by: null,
		is_published: true,
		has_unpublished_changes: false,
		access_level: "authenticated",
		app_model: "standalone_v2",
		is_solution_managed: false,
		solution_id: null,
		role_ids: [],
		repo_path: null,
		logo: null,
		logo_url: null,
		logo_version: null,
		sdk_package_version: "1.0.0",
		sdk_fingerprint: "old",
		sdk_contract_version: 1,
		sdk_built_at: NOW,
		sdk_status: "update_available",
		sdk_source_available: true,
		...overrides,
	};
}

async function mockSdkUpdateFixtures(page: Page) {
	await page.route("**/api/applications**", async (route) => {
		await route.fulfill({
			json: {
				applications: [
					app({}),
					app({
						id: "22222222-2222-2222-2222-222222222222",
						name: "Asset Intake",
						slug: "asset-intake",
						description: "Source was not retained.",
						sdk_status: "update_required",
						sdk_source_available: false,
					}),
					app({
						id: "33333333-3333-3333-3333-333333333333",
						name: "Client Portal",
						slug: "client-portal",
						description: "Already rebuilt.",
						sdk_status: "current",
						sdk_source_available: true,
					}),
				],
				total: 3,
			},
		});
	});
	await page.route(
		"**/api/applications/11111111-1111-1111-1111-111111111111/sdk/update",
		async (route) => {
			await route.fulfill({
				json: {
					job_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
					status: "queued",
					reused: false,
					notification_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
				},
			});
		},
	);
}

test.describe("Applications SDK update UI", () => {
	test("desktop shows update available, updating, and source-unavailable states", async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1280, height: 900 });
		await mockSdkUpdateFixtures(page);

		await page.goto("/apps");
		await expect(page.getByText("SDK update available")).toBeVisible();
		await expect(page.getByText("SDK update required")).toBeVisible();

		await page
			.getByRole("button", { name: "Dispatch Board actions" })
			.click();
		await page.getByRole("menuitem", { name: "Update SDK" }).click();

		await expect(page.getByLabel("Updating SDK")).toBeVisible();
		await page.keyboard.press("Escape");

		await page
			.getByRole("button", { name: "Asset Intake actions" })
			.click();
		await expect(
			page.getByRole("menuitem", { name: "Source unavailable" }),
		).toHaveAttribute("aria-disabled", "true");
		await page.keyboard.press("Escape");

		await page.screenshot({
			path: test.info().outputPath("sdk-update-desktop.png"),
			fullPage: true,
		});

		await page.getByRole("radio", { name: "Table view" }).click();
		await expect(page.getByRole("cell", { name: /SDK current/ })).toBeVisible();
		await expect(
			page.getByLabel("SDK update required; source unavailable"),
		).toBeVisible();
		await page
			.getByRole("button", { name: "Dispatch Board actions" })
			.click();
		await expect(
			page.getByRole("menuitem", { name: "Updating SDK" }),
		).toHaveAttribute("aria-disabled", "true");
		await page.screenshot({
			path: test.info().outputPath("sdk-update-table.png"),
			fullPage: true,
		});
	});

	test("mobile keeps SDK update affordances inside each card overflow", async ({
		page,
	}) => {
		await page.setViewportSize({ width: 390, height: 844 });
		await mockSdkUpdateFixtures(page);

		await page.goto("/apps");
		await expect(page.getByText("SDK update available")).toBeVisible();
		await expect(page.getByText("SDK update required")).toBeVisible();

		await page
			.getByRole("button", { name: "Dispatch Board actions" })
			.click();
		await page.getByRole("menuitem", { name: "Update SDK" }).click();
		await expect(page.getByLabel("Updating SDK")).toBeVisible();

		await page.screenshot({
			path: test.info().outputPath("sdk-update-mobile.png"),
			fullPage: true,
		});
	});
});
