import { test, expect, type AuthedApi } from "./fixtures/api-fixture";

const UNIQUE = `${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
const ORG_NAME = `Config Acceptance ${UNIQUE}`;
const CONFIG_KEY = `E2E_CONFIG_${UNIQUE}`;
const ORIGINAL_VALUE = `original-${UNIQUE}`;
const EDITED_VALUE = `edited-${UNIQUE}`;
const DESCRIPTION = `Created by config acceptance ${UNIQUE}`;
const EDITED_DESCRIPTION = `Edited by config acceptance ${UNIQUE}`;

type Organization = { id: string; name: string };
type ConfigRecord = {
	id?: string | null;
	key: string;
	value: unknown;
	type: string;
	org_id?: string | null;
	scope: string;
	description?: string | null;
};

async function expectOk(
	response: Pick<Awaited<ReturnType<AuthedApi["get"]>>, "ok" | "text">,
) {
	expect(response.ok(), await response.text()).toBe(true);
}

async function createOrganization(api: AuthedApi, name: string) {
	const response = await api.post("/api/organizations", {
		data: {
			name,
			domain: `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.gobifrost.dev`,
		},
	});
	await expectOk(response);
	return (await response.json()) as Organization;
}

async function readConfig(api: AuthedApi, key: string) {
	const response = await api.get("/api/config");
	await expectOk(response);
	const configs = (await response.json()) as ConfigRecord[];
	return configs.find((config) => config.key === key);
}

async function expectDeleted(
	response: Awaited<ReturnType<AuthedApi["delete"]>>,
) {
	expect([200, 204, 404]).toContain(response.status());
}

test("[CONFIG-01] admin creates edits reloads and deletes org-scoped configuration", async ({
	page,
	api,
}) => {
	const organization = await createOrganization(api, ORG_NAME);
	let configId: string | null = null;

	try {
		await page.goto("/config");
		await expect(
			page.getByRole("heading", { name: "Configuration", exact: true }),
		).toBeVisible({ timeout: 10_000 });

		await page.getByRole("button", { name: "Add configuration" }).first().click();
		const addDialog = page.getByRole("dialog", {
			name: "Add Configuration",
		});
		await expect(addDialog).toBeVisible();
		await addDialog.getByRole("combobox", { name: "Organization" }).click();
		await page.getByRole("option", { name: ORG_NAME }).click();
		await addDialog.getByLabel("Key").fill(CONFIG_KEY);
		await addDialog.getByLabel("Value").fill(ORIGINAL_VALUE);
		await addDialog.getByLabel("Description (Optional)").fill(DESCRIPTION);

		const createRequest = page.waitForResponse(
			(response) =>
				response.request().method() === "POST" &&
				response.url().endsWith("/api/config"),
		);
		await addDialog.getByRole("button", { name: "Create" }).click();
		const createResponse = await createRequest;
		await expectOk(createResponse);
		const created = (await createResponse.json()) as ConfigRecord;
		configId = created.id ?? null;
		expect(created).toMatchObject({
			key: CONFIG_KEY,
			value: ORIGINAL_VALUE,
			type: "string",
			org_id: organization.id,
			scope: "org",
			description: DESCRIPTION,
		});
		await expect(addDialog).toHaveCount(0);

		await page
			.getByRole("textbox", { name: "Search configuration" })
			.fill(CONFIG_KEY);
		await expect(
			page.getByRole("button", { name: CONFIG_KEY, exact: true }),
		).toBeVisible({
			timeout: 10_000,
		});
		await expect(page.getByText(ORG_NAME, { exact: true })).toBeVisible();
		await expect(page.getByText(ORIGINAL_VALUE, { exact: true })).toBeVisible();

		await page.getByRole("button", { name: CONFIG_KEY, exact: true }).click();
		const editDialog = page.getByRole("dialog", {
			name: "Edit Configuration",
		});
		await expect(editDialog).toBeVisible();
		await expect(editDialog.getByLabel("Key")).toHaveValue(CONFIG_KEY);
		await expect(editDialog.getByLabel("Value")).toHaveValue(
			ORIGINAL_VALUE,
		);
		await editDialog.getByLabel("Value").fill(EDITED_VALUE);
		await editDialog
			.getByLabel("Description (Optional)")
			.fill(EDITED_DESCRIPTION);

		const updateRequest = page.waitForResponse(
			(response) =>
				response.request().method() === "PUT" &&
				!!configId &&
				response.url().endsWith(`/api/config/${configId}`),
		);
		await editDialog.getByRole("button", { name: "Update" }).click();
		const updateResponse = await updateRequest;
		await expectOk(updateResponse);
		expect(await updateResponse.json()).toMatchObject({
			id: configId,
			key: CONFIG_KEY,
			value: EDITED_VALUE,
			type: "string",
			org_id: organization.id,
			scope: "org",
			description: EDITED_DESCRIPTION,
		});
		await expect(editDialog).toHaveCount(0);

		await page.reload();
		await expect(
			page.getByRole("heading", { name: "Configuration", exact: true }),
		).toBeVisible({ timeout: 10_000 });
		await page
			.getByRole("textbox", { name: "Search configuration" })
			.fill(CONFIG_KEY);
		await expect(
			page.getByRole("button", { name: CONFIG_KEY, exact: true }),
		).toBeVisible({
			timeout: 10_000,
		});
		await expect(page.getByText(EDITED_VALUE, { exact: true })).toBeVisible();
		await expect(page.getByText(EDITED_DESCRIPTION, { exact: true })).toBeVisible();

		const persisted = await readConfig(api, CONFIG_KEY);
		expect(persisted).toMatchObject({
			id: configId,
			key: CONFIG_KEY,
			value: EDITED_VALUE,
			type: "string",
			org_id: organization.id,
			scope: "org",
			description: EDITED_DESCRIPTION,
		});

		const deleteRequest = page.waitForResponse(
			(response) =>
				response.request().method() === "DELETE" &&
				!!configId &&
				response.url().endsWith(`/api/config/${configId}`),
		);
		await page
			.getByRole("button", { name: `More actions for ${CONFIG_KEY}` })
			.click();
		await page.getByRole("menuitem", { name: "Delete" }).click();
		const deleteDialog = page.getByRole("alertdialog", {
			name: "Delete configuration",
		});
		await expect(deleteDialog).toBeVisible();
		await deleteDialog
			.getByRole("button", { name: "Delete configuration" })
			.click();
		const deleteResponse = await deleteRequest;
		expect(deleteResponse.status()).toBe(204);
		configId = null;
		await expect(deleteDialog).toHaveCount(0);
		await expect(
			page.getByRole("button", { name: CONFIG_KEY, exact: true }),
		).toHaveCount(0);

		expect(await readConfig(api, CONFIG_KEY)).toBeUndefined();
	} finally {
		if (configId) {
			await expectDeleted(await api.delete(`/api/config/${configId}`));
		}
		await expectDeleted(
			await api.delete(`/api/organizations/${organization.id}`),
		);
	}
});
