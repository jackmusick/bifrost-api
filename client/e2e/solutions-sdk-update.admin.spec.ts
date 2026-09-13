/**
 * Solution SDK aggregate UI (Admin)
 *
 * Uses explicit dev fixture route data for deterministic screenshots while
 * rendering the real Solutions list/detail components. The fixture exercises
 * the durable PlatformJob WebSocket update path; it does not poll.
 */

import { test, expect } from "./fixtures/api-fixture";
import type { Page } from "@playwright/test";

const NOW = "2026-09-12T12:00:00Z";
const SOLUTION_ID = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa";
const APP_ID = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb";
const JOB_ID = "cccccccc-3333-4333-8333-cccccccccccc";

function solution(overrides: Record<string, unknown> = {}) {
	return {
		id: SOLUTION_ID,
		slug: "sdk-solution",
		name: "SDK Solution",
		organization_id: null,
		global_repo_access: false,
		git_connected: false,
		git_repo_url: null,
		repo_subpath: null,
		git_ref: null,
		version: "1.0.0",
		upgraded_from_version: null,
		update_available_version: null,
		setup_complete: true,
		status: "active",
		entity_counts: {
			workflows: 0,
			apps: 1,
			forms: 0,
			agents: 0,
			tables: 0,
			claims: 0,
			files: 0,
		},
		sdk_status: "update_available",
		sdk_actionable_count: 1,
		logo_url: null,
		logo_version: null,
		scope: "global",
		...overrides,
	};
}

function entities() {
	return {
		solution: solution(),
		workflows: [],
		apps: [
			{
				id: APP_ID,
				name: "Solution Console",
				slug: "solution-console",
				description: "Managed app with retained source.",
				app_model: "standalone_v2",
				is_published: true,
				has_unpublished_changes: false,
				logo_url: null,
				sdk_status: "update_available",
				sdk_source_available: true,
			},
		],
		forms: [],
		agents: [],
		tables: [],
		claims: [],
		configs: [],
		required_configs_unset: [],
		files: [],
	};
}

async function mockSolutionSdkFixtures(page: Page) {
	let sendSocketMessage: ((payload: Record<string, unknown>) => void) | undefined;
	await page.routeWebSocket(/\/ws\/connect/, (socket) => {
		sendSocketMessage = (payload) => socket.send(JSON.stringify(payload));
		socket.onMessage((raw) => {
			const payload = JSON.parse(String(raw)) as Record<string, unknown>;
			if (payload.type === "subscribe") {
				for (const channel of (payload.channels as string[]) ?? []) {
					sendSocketMessage?.({ type: "subscribed", channel });
				}
			}
			if (payload.type === "ping") {
				socket.send(JSON.stringify({ type: "pong" }));
			}
		});
	});

	await page.route("**/api/solutions", async (route) => {
		await route.fulfill({
			json: {
				solutions: [
					solution(),
					solution({
						id: "dddddddd-4444-4444-8444-dddddddddddd",
						slug: "current-solution",
						name: "Current Solution",
						sdk_status: "current",
						sdk_actionable_count: 0,
					}),
				],
			},
		});
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/entities`, async (route) => {
		await route.fulfill({ json: entities() });
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/setup`, async (route) => {
		await route.fulfill({ json: { setup_complete: true, items: [] } });
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/readme`, async (route) => {
		await route.fulfill({ json: { readme: null } });
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/export-jobs`, async (route) => {
		await route.fulfill({ json: { jobs: [] } });
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/sdk/status`, async (route) => {
		await route.fulfill({
			json: {
				solution_id: SOLUTION_ID,
				sdk_status: "update_available",
				actionable_count: 1,
				apps: [
					{
						application_id: APP_ID,
						slug: "solution-console",
						sdk_status: "update_available",
						sdk_source_available: true,
						actionable: true,
					},
				],
			},
		});
	});
	await page.route(`**/api/solutions/${SOLUTION_ID}/sdk/update`, async (route) => {
		await route.fulfill({
			json: {
				solution_id: SOLUTION_ID,
				accepted: [
					{
						application_id: APP_ID,
						job_id: JOB_ID,
						status: "queued",
						reused: false,
						notification_id: null,
					},
				],
				skipped: [],
			},
		});
	});

	return {
		startUpdate() {
			if (!sendSocketMessage) {
				throw new Error("Solution SDK update websocket did not connect");
			}
			sendSocketMessage({
				type: "platform_job_updated",
				job: {
					id: JOB_ID,
					job_type: "application.sdk_update",
					payload_version: 1,
					resource_type: "application",
					resource_id: APP_ID,
					resource_lock_key: `application:${APP_ID}`,
					priority: 100,
					title: "Update application SDK",
					requested_by_user_id: "fixture-user",
					requested_by_name: "Fixture Admin",
					status: "running",
					progress: { current: 0, total: 1, percent: 0 },
					revision: 2,
					attempt: 1,
					max_attempts: 1,
					can_cancel: false,
					created_at: NOW,
					updated_at: NOW,
				},
			});
		},
	};
}

test.describe("Solutions SDK aggregate UI", () => {
	test("shows list aggregate status and detail in-progress update-all state", async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1280, height: 900 });
		const fixture = await mockSolutionSdkFixtures(page);

		await page.goto("/solutions");
		await expect(page.getByRole("heading", { name: "Solutions" })).toBeVisible();
		await expect(page.getByText("SDK Solution")).toBeVisible();
		await expect(page.getByLabel("SDK update available")).toBeVisible();
		await expect(page.getByLabel("1 app can update SDK")).toBeVisible();
		await page.screenshot({
			path: test.info().outputPath("solution-sdk-list.png"),
			fullPage: true,
		});

		await page.getByRole("link", { name: /SDK Solution/ }).click();
		await expect(page.getByTestId("solution-detail")).toBeVisible();
		await expect(page.getByLabel("SDK update available")).toBeVisible();

		await page.getByTestId("solution-actions").click();
		await page.getByTestId("update-solution-app-sdks").click();
		await expect(page.getByTestId("update-solution-app-sdks")).toBeHidden();
		fixture.startUpdate();
		await page.getByTestId("solution-actions").focus();
		await page.keyboard.press("Enter");
		const updatingItem = page.getByRole("menuitem", {
			name: /Updating app SDKs/,
		});
		await expect(updatingItem).toBeVisible();
		await expect(updatingItem).toHaveAttribute("aria-disabled", "true");
		await page.screenshot({
			path: test.info().outputPath("solution-sdk-detail-updating.png"),
			fullPage: true,
		});
	});
});
