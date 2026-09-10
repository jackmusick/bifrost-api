/**
 * Entity Management Acceptance (Admin)
 *
 * Covers the primary browser journey for assigning entity organization scope:
 * an admin selects one app entity, assigns it to an organization, reassigns it
 * to another organization, then returns it to Global. The second seeded app is
 * intentionally left unselected and verified unchanged through the API.
 */

import type { Locator, Page } from "@playwright/test";
import { test, expect, type AuthedApi } from "./fixtures/api-fixture";

type Organization = { id: string; name: string };
type Application = {
	id: string;
	slug: string;
	name: string;
	organization_id: string | null;
};

const UNIQUE = `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
const ORG_ONE_NAME = `E2E Entity Scope One ${UNIQUE}`;
const ORG_TWO_NAME = `E2E Entity Scope Two ${UNIQUE}`;
const SELECTED_APP_NAME = `E2E Entity Managed App ${UNIQUE}`;
const SELECTED_APP_SLUG = `e2e-entity-managed-${UNIQUE}`;
const UNSELECTED_APP_NAME = `E2E Entity Untouched App ${UNIQUE}`;
const UNSELECTED_APP_SLUG = `e2e-entity-untouched-${UNIQUE}`;

function endpoint(path: string): string {
	return path;
}

async function expectOk(
	response: { ok(): boolean; status(): number },
	method: string,
	path: string,
) {
	expect(
		response.ok(),
		`${method} ${endpoint(path)} returned ${response.status()}`,
	).toBe(true);
}

async function createOrganization(
	api: AuthedApi,
	name: string,
	domainPrefix: string,
): Promise<Organization> {
	const path = "/api/organizations";
	const response = await api.post(path, {
		data: {
			name,
			domain: `${domainPrefix}-${UNIQUE}.example`,
		},
	});
	await expectOk(response, "POST", path);
	return (await response.json()) as Organization;
}

async function createApplication(
	api: AuthedApi,
	name: string,
	slug: string,
): Promise<Application> {
	const path = "/api/applications";
	const response = await api.post(path, {
		data: {
			name,
			slug,
			access_level: "authenticated",
			role_ids: [],
			organization_id: null,
			// Entity management only needs metadata. Pin the legacy inline model so
			// create does not require a standalone Solution deployment fixture.
			app_model: "inline_v1",
		},
	});
	await expectOk(response, "POST", path);
	return (await response.json()) as Application;
}

async function readApplication(
	api: AuthedApi,
	slug: string,
): Promise<Application> {
	const path = `/api/applications/${slug}`;
	const response = await api.get(path);
	await expectOk(response, "GET", "/api/applications/{slug}");
	return (await response.json()) as Application;
}

async function cleanupApplication(api: AuthedApi, appId: string | undefined) {
	if (!appId) return;
	const response = await api.delete(`/api/applications/${appId}`);
	expect(
		[204, 404],
		`DELETE /api/applications/{app_id} returned ${response.status()}`,
	).toContain(response.status());
}

async function cleanupOrganization(
	api: AuthedApi,
	organizationId: string | undefined,
) {
	if (!organizationId) return;
	const response = await api.delete(`/api/organizations/${organizationId}`);
	expect(
		[204, 404],
		`DELETE /api/organizations/{org_id} returned ${response.status()}`,
	).toContain(response.status());
}

function entityCard(page: Page, name: string): Locator {
	return page
		.getByRole("checkbox", { name: `Select ${name}` })
		.locator("xpath=ancestor::div[contains(@class, 'cursor-grab')][1]");
}

async function openEntityManagement(page: Page) {
	await page.goto("/entity-management");
	await expect(
		page.getByRole("heading", { name: "Entity Management" }),
	).toBeVisible({ timeout: 10000 });
}

async function filterToApp(page: Page, name: string) {
	await page.getByRole("textbox", { name: "Search entities" }).fill(name);
	await expect(
		page.getByRole("checkbox", { name: `Select ${name}` }),
	).toBeVisible({ timeout: 10000 });
}

async function assignSelectedEntityTo(page: Page, destinationName: string) {
	const assignment = page.getByRole("region", { name: "Entity assignment" });
	await expect(assignment).toBeVisible();
	await assignment
		.getByRole("button", {
			name: `Apply ${destinationName} to 1 selected entities`,
		})
		.click();

	const dialog = page.getByRole("dialog", { name: "Change organization" });
	await expect(dialog).toBeVisible();
	await expect(
		dialog.getByRole("list", { name: "Entities to update" }),
	).toContainText(SELECTED_APP_NAME);
	await dialog.getByRole("button", { name: "Apply changes" }).click();
	await expect(dialog).toBeHidden({ timeout: 10000 });
}

async function expectAppScope(
	api: AuthedApi,
	slug: string,
	organizationId: string | null,
) {
	await expect
		.poll(async () => (await readApplication(api, slug)).organization_id, {
			message: `${slug} organization scope`,
		})
		.toBe(organizationId);
}

test.describe("Entity management acceptance", () => {
	let orgOne: Organization | undefined;
	let orgTwo: Organization | undefined;
	let selectedApp: Application | undefined;
	let unselectedApp: Application | undefined;

	test.beforeAll(async ({ api }) => {
		orgOne = await createOrganization(
			api,
			ORG_ONE_NAME,
			"entity-scope-one",
		);
		orgTwo = await createOrganization(
			api,
			ORG_TWO_NAME,
			"entity-scope-two",
		);
		selectedApp = await createApplication(
			api,
			SELECTED_APP_NAME,
			SELECTED_APP_SLUG,
		);
		unselectedApp = await createApplication(
			api,
			UNSELECTED_APP_NAME,
			UNSELECTED_APP_SLUG,
		);
	});

	test.afterAll(async ({ api }) => {
		await cleanupApplication(api, selectedApp?.id);
		await cleanupApplication(api, unselectedApp?.id);
		await cleanupOrganization(api, orgOne?.id);
		await cleanupOrganization(api, orgTwo?.id);
	});

	test("assigns, reassigns, and unassigns one entity while preserving an unselected resource", async ({
		page,
		api,
	}) => {
		expect(orgOne).toBeDefined();
		expect(orgTwo).toBeDefined();
		expect(selectedApp).toBeDefined();
		expect(unselectedApp).toBeDefined();

		await openEntityManagement(page);
		await filterToApp(page, SELECTED_APP_NAME);

		const selectedCard = entityCard(page, SELECTED_APP_NAME);
		await expect(selectedCard).toContainText("Global");
		await page
			.getByRole("checkbox", { name: `Select ${SELECTED_APP_NAME}` })
			.check();
		await expect(page.getByText("1 selected").first()).toBeVisible();

		await assignSelectedEntityTo(page, ORG_ONE_NAME);
		await expectAppScope(api, SELECTED_APP_SLUG, orgOne!.id);
		await expectAppScope(api, UNSELECTED_APP_SLUG, null);
		await expect(selectedCard).toContainText(ORG_ONE_NAME);

		await page.reload();
		await filterToApp(page, SELECTED_APP_NAME);
		await expect(entityCard(page, SELECTED_APP_NAME)).toContainText(
			ORG_ONE_NAME,
		);
		await page
			.getByRole("checkbox", { name: `Select ${SELECTED_APP_NAME}` })
			.check();

		await assignSelectedEntityTo(page, ORG_TWO_NAME);
		await expectAppScope(api, SELECTED_APP_SLUG, orgTwo!.id);
		await expectAppScope(api, UNSELECTED_APP_SLUG, null);
		await expect(entityCard(page, SELECTED_APP_NAME)).toContainText(
			ORG_TWO_NAME,
		);

		await assignSelectedEntityTo(page, "Global");
		await expectAppScope(api, SELECTED_APP_SLUG, null);
		await expectAppScope(api, UNSELECTED_APP_SLUG, null);
		await expect(entityCard(page, SELECTED_APP_NAME)).toContainText(
			"Global",
		);
	});
});
