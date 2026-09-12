/**
 * Bulk user actions — admin (Block 2).
 *
 * Drives the new selection checkbox column + BulkActionBar to verify the
 * happy path: select N users → "Move to org" → toast → reload → persisted
 * users reflect the selected move while unselected rows stay put.
 *
 * Avoids touching the platform_admin row (you can't bulk-act on yourself —
 * the row's checkbox is disabled with a tooltip).
 */

import { test, expect } from "./fixtures/api-fixture";
import type { AuthedApi } from "./fixtures/api-fixture";

const SUFFIX = Math.random().toString(36).slice(2, 8);
const SOURCE_ORG_NAME = `Bulk Source ${SUFFIX}`;
const DEST_ORG_NAME = `Bulk Dest ${SUFFIX}`;
const USER_PREFIX = `bulk-spec-${SUFFIX}`;
const SELECTED_USER_COUNT = 2;
const SEEDED_USER_COUNT = 3;

let sourceOrgId = "";
let destOrgId = "";
const seededUserIds: string[] = [];

type BulkUser = {
	id: string;
	email: string;
	name?: string | null;
	organization_id: string | null;
};

async function listSeededUsers(api: AuthedApi) {
	const response = await api.get("/api/users", {
		params: {
			include_inactive: true,
			search: USER_PREFIX,
			sort_by: "email",
			sort_direction: "asc",
			limit: 10,
			offset: 0,
		},
	});
	expect(response.ok(), await response.text()).toBe(true);
	const users = (await response.json()) as BulkUser[];
	return users.filter((user) => user.email.startsWith(USER_PREFIX));
}

test.describe("Bulk user actions", () => {
	test.beforeAll(async ({ api }) => {
		// Source + destination orgs so the move target is unambiguous.
		const sourceResp = await api.post("/api/organizations", {
			data: {
				name: SOURCE_ORG_NAME,
				domain: `${USER_PREFIX}-src.gobifrost.dev`,
			},
		});
		expect(sourceResp.ok(), await sourceResp.text()).toBe(true);
		const source = await sourceResp.json();
		sourceOrgId = source.id;

		const destResp = await api.post("/api/organizations", {
			data: {
				name: DEST_ORG_NAME,
				domain: `${USER_PREFIX}-dst.gobifrost.dev`,
			},
		});
		expect(destResp.ok(), await destResp.text()).toBe(true);
		const dest = await destResp.json();
		destOrgId = dest.id;

		for (let i = 0; i < SEEDED_USER_COUNT; i++) {
			const r = await api.post("/api/users", {
				data: {
					email: `${USER_PREFIX}-${i}@bulkspec.gobifrost.dev`,
					name: `${USER_PREFIX}-${i}`,
					organization_id: source.id,
					is_superuser: false,
					invite: false,
				},
			});
			expect(r.ok(), `Create user ${i} failed: ${await r.text()}`).toBe(
				true,
			);
			seededUserIds.push(((await r.json()) as { id: string }).id);
		}
	});

	test.afterAll(async ({ api }) => {
		for (const id of seededUserIds) {
			const response = await api.delete(`/api/users/${id}`);
			expect([200, 204, 404]).toContain(response.status());
		}
		if (sourceOrgId)
			expect([200, 204, 404]).toContain(
				(
					await api.delete(`/api/organizations/${sourceOrgId}`)
				).status(),
			);
		if (destOrgId)
			expect([200, 204, 404]).toContain(
				(await api.delete(`/api/organizations/${destOrgId}`)).status(),
			);
	});

	test("[USER-01] bulk move persists selected users after reload and leaves unselected users", async ({
		page,
		api,
	}) => {
		await page.goto("/users");
		await expect(
			page.getByRole("heading", { name: /users/i }).first(),
		).toBeVisible({ timeout: 10000 });
		await page
			.getByPlaceholder("Search users by email or name...")
			.fill(USER_PREFIX);

		// Wait for the table to render with our seeded users.
		await expect(page.getByText(`${USER_PREFIX}-0`).first()).toBeVisible({
			timeout: 10000,
		});

		// Tick only two row checkboxes so the third seeded user proves the
		// operation did not move unrelated visible rows.
		for (let i = 0; i < SELECTED_USER_COUNT; i++) {
			const checkbox = page.getByRole("checkbox", {
				name: new RegExp(`Select ${USER_PREFIX}-${i}`),
			});
			await checkbox.click();
		}

		// The sticky bulk action bar appears with the count.
		const actionBar = page.getByRole("region", {
			name: /bulk user actions/i,
		});
		await expect(actionBar).toBeVisible();
		await expect(
			actionBar.getByText(`${SELECTED_USER_COUNT} selected`),
		).toBeVisible();

		// Open the move-to-org dialog.
		await actionBar.getByRole("button", { name: /move to org/i }).click();
		const dialog = page.getByRole("dialog");
		await expect(
			dialog.getByText(
				new RegExp(`move ${SELECTED_USER_COUNT} user`, "i"),
			),
		).toBeVisible();

		// Pick the destination org from the OrganizationSelect.
		await dialog.getByRole("combobox").click();
		await page.getByRole("option", { name: DEST_ORG_NAME }).click();

		// Submit and watch for the success toast.
		await dialog.getByRole("button", { name: /move users/i }).click();
		await expect(
			page.getByText(
				new RegExp(`move to org \\(${SELECTED_USER_COUNT}\\)`, "i"),
			),
		).toBeVisible({ timeout: 10000 });

		await page.reload();
		await page
			.getByPlaceholder("Search users by email or name...")
			.fill(USER_PREFIX);
		await expect(page.getByText(`${USER_PREFIX}-0`).first()).toBeVisible({
			timeout: 10000,
		});

		const users = await listSeededUsers(api);
		expect(users).toHaveLength(SEEDED_USER_COUNT);
		const byName = new Map(users.map((user) => [user.name, user]));
		for (let i = 0; i < SELECTED_USER_COUNT; i++) {
			expect(byName.get(`${USER_PREFIX}-${i}`)?.organization_id).toBe(
				destOrgId,
			);
		}
		expect(
			byName.get(`${USER_PREFIX}-${SEEDED_USER_COUNT - 1}`)
				?.organization_id,
		).toBe(sourceOrgId);
	});
});
