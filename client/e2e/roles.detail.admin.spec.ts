/**
 * Roles detail + consumer tabs — admin (Block 4/5).
 *
 * Drives the new card-grid + RoleDetail page + AssignDrawer flow:
 *  - Roles list shows cards with chips
 *  - Click a chip → land on the right tab
 *  - Open Assign drawer for users → tick a user → submit
 *  - Verify the user appears in the assigned list
 *  - Multi-select + bulk unassign drops them back to empty
 */

import { test, expect, type AuthedApi } from "./fixtures/api-fixture";

const SUFFIX = Math.random().toString(36).slice(2, 8);
const ROLE_NAME = `RoleDetail ${SUFFIX}`;
const USER_EMAIL = `roledetail-${SUFFIX}@e2e.gobifrost.dev`;
const FORM_NAME = `RoleDetail Form ${SUFFIX}`;
const WORKFLOW_PATH = `e2e_role_detail_form_${SUFFIX}.py`;
const WORKFLOW_FN = `e2e_role_detail_form_${SUFFIX}`;
const WORKFLOW_SOURCE = `from bifrost import workflow

@workflow(name="${WORKFLOW_FN}")
async def ${WORKFLOW_FN}(summary: str):
    return {"summary": summary}
`;

type RoleFormsResponse = { form_ids: string[] };

type StatusResponse = {
	ok(): boolean;
	status(): number;
};

async function expectOk(
	response: StatusResponse,
	label: string,
) {
	expect(response.ok(), `${label}: ${response.status()}`).toBe(true);
}

async function expectDeleted(
	response: Awaited<ReturnType<AuthedApi["delete"]>>,
	label: string,
) {
	expect([200, 204, 404], `${label}: ${response.status()}`).toContain(
		response.status(),
	);
}

async function readRoleForms(
	api: AuthedApi,
	roleId: string,
): Promise<RoleFormsResponse> {
	const response = await api.get(`/api/roles/${roleId}/forms`);
	await expectOk(response, "read role forms");
	return (await response.json()) as RoleFormsResponse;
}

test.describe("Roles detail", () => {
	let roleId: string;
	let userId: string;
	let formId: string;

	test.beforeAll(async ({ api }) => {
		// Create a fresh role.
		const r = await api.post("/api/roles", {
			data: { name: ROLE_NAME, description: "e2e detail page" },
		});
		await expectOk(r, "create role");
		roleId = (await r.json()).id;

		// Find / create an org we can put the user in.
		const orgsResp = await api.get("/api/organizations");
		const orgs = (await orgsResp.json()) as { id: string }[];
		const orgId = orgs[0]?.id;
		expect(orgId, "need at least one org").toBeTruthy();

		const write = await api.put("/api/files/editor/content", {
			data: {
				path: WORKFLOW_PATH,
				content: WORKFLOW_SOURCE,
				encoding: "utf-8",
			},
		});
		await expectOk(write, "write role form workflow");

		const registration = await api.post("/api/workflows/register", {
			data: {
				path: WORKFLOW_PATH,
				function_name: WORKFLOW_FN,
				organization_id: orgId,
			},
		});
		await expectOk(registration, "register role form workflow");
		const registered = (await registration.json()) as { id?: string };
		let workflowId = registered.id;
		if (!workflowId) {
			const workflows = await api.get("/api/workflows", {
				params: { scope: orgId },
			});
			await expectOk(workflows, "read role form workflow");
			workflowId = (
				(await workflows.json()) as Array<{ id: string; name: string }>
			).find((item) => item.name === WORKFLOW_FN)?.id;
		}
		expect(workflowId, "registered role form workflow id").toBeTruthy();

		const form = await api.post("/api/forms", {
			data: {
				name: FORM_NAME,
				description: `Role form consumer ${SUFFIX}`,
				workflow_id: workflowId!,
				organization_id: orgId,
				form_schema: {
					fields: [
						{
							name: "summary",
							label: "Summary",
							type: "text",
							required: true,
						},
					],
				},
				access_level: "role_based",
			},
		});
		await expectOk(form, "create role form consumer");
		formId = ((await form.json()) as { id: string }).id;

		const u = await api.post("/api/users", {
			data: {
				email: USER_EMAIL,
				name: `RoleDetail User ${SUFFIX}`,
				organization_id: orgId,
				is_superuser: false,
				invite: false,
			},
		});
		await expectOk(u, "create role user");
		userId = (await u.json()).id;

		const assign = await api.post(`/api/roles/${roleId}/users`, {
			data: { user_ids: [userId] },
		});
		await expectOk(assign, "seed role user assignment");
	});

	test.afterAll(async ({ api }) => {
		if (formId)
			await expectDeleted(
				await api.delete(`/api/forms/${formId}`),
				"delete role form consumer",
			);
		await expectDeleted(
			await api.delete(
				`/api/files/editor?path=${encodeURIComponent(WORKFLOW_PATH)}`,
			),
			"delete role form workflow source",
		);
		if (userId)
			await expectDeleted(
				await api.delete(`/api/users/${userId}`),
				"delete role user",
			);
		if (roleId)
			await expectDeleted(
				await api.delete(`/api/roles/${roleId}`),
				"delete role",
			);
	});

	test("card → users chip → drawer → assigned → unassign", async ({
		page,
	}) => {
		await page.goto("/roles");

		// The card for our role is rendered with name visible.
		await expect(page.getByText(ROLE_NAME).first()).toBeVisible({
			timeout: 10000,
		});

		// Navigate directly via the URL — the click-the-chip path is exercised
		// in the vitest. This spec focuses on the assignment lifecycle, not on
		// re-validating the chip nav.
		await page.goto(`/roles/${roleId}/users`);

		// We're on the detail page.
		await expect(
			page.getByRole("heading", { name: ROLE_NAME }),
		).toBeVisible();

		// The role endpoint returns complete user display data. The page never
		// exposes an assignment UUID while waiting for the user directory.
		await expect(
			page.getByText(new RegExp(`RoleDetail User ${SUFFIX}`)),
		).toBeVisible();
		await expect(page.getByText(userId, { exact: true })).toHaveCount(0);
		await expect(
			page.getByRole("navigation", { name: "List pagination" }),
		).toHaveText("1–1 of 1 · Page 1 of 1");

		// Remove the seeded assignment so the rest of the test exercises the
		// empty → assign → assigned lifecycle.
		await page
			.getByLabel(new RegExp(`Select RoleDetail User ${SUFFIX}`))
			.click();
		await page.getByRole("button", { name: /unassign from role/i }).click();
		await expect(
			page.getByText(/no users assigned to this role yet/i),
		).toBeVisible();

		// Open the drawer.
		await page.getByRole("button", { name: /assign users/i }).click();
		await expect(
			page.getByText(/pick the users you want to add/i),
		).toBeVisible();

		// Tick our seeded user (drawer renders candidates).
		const pickRow = page.getByLabel(new RegExp(`Pick .*${SUFFIX}`));
		await pickRow.first().click();

		await page.getByRole("button", { name: /assign 1/i }).click();

		// Toast confirms.
		await expect(page.getByText(/assigned 1 users/i)).toBeVisible({
			timeout: 10000,
		});

		// Close the drawer (it stays open after submit per design) so the
		// underlying tab's checkbox isn't ambiguous with the drawer's.
		// Use the SheetClose icon-button (the dialog's primary close), not our
		// outline footer Close button — there are two "Close" buttons in the
		// drawer DOM.
		await page
			.getByRole("dialog")
			.getByRole("button", { name: /^close$/i })
			.last()
			.click();

		// User is now in the assigned list.
		await expect(
			page.getByText(new RegExp(`RoleDetail User ${SUFFIX}`)),
		).toBeVisible();

		// Assigned users open the same detail route as rows on the Users page.
		await page.getByText(new RegExp(`RoleDetail User ${SUFFIX}`)).click();
		await expect(page).toHaveURL(new RegExp(`/users/${userId}$`));
		await page.goBack();
		await expect(page).toHaveURL(new RegExp(`/roles/${roleId}/users$`));
		await expect(
			page.getByRole("heading", { name: ROLE_NAME }),
		).toBeVisible();

		// Tick + unassign.
		await page
			.getByLabel(new RegExp(`Select RoleDetail User ${SUFFIX}`))
			.click();
		await page.getByRole("button", { name: /unassign from role/i }).click();

		// This flow removes the user twice; target the newest toast so the earlier
		// notification still fading out does not make the locator ambiguous.
		await expect(
			page.locator('[data-sonner-toast][data-front="true"]'),
		).toContainText(/removed 1 users/i, {
			timeout: 10000,
		});
		await expect(
			page.getByText(/no users assigned to this role yet/i),
		).toBeVisible();
	});

	test("forms tab assigns, reloads, unassigns, and persists role membership", async ({
		page,
		api,
	}) => {
		expect((await readRoleForms(api, roleId)).form_ids).not.toContain(
			formId,
		);

		await page.goto(`/roles/${roleId}/forms`);
		await expect(
			page.getByRole("heading", { name: ROLE_NAME }),
		).toBeVisible({ timeout: 10_000 });
		await expect(
			page.getByRole("tab", { name: /forms\s+0/i }),
		).toBeVisible();
		await expect(
			page.getByText(/no forms assigned to this role yet/i),
		).toBeVisible();

		await page.getByRole("button", { name: /assign forms/i }).click();
		const drawer = page.getByRole("dialog", { name: "Assign forms" });
		await expect(drawer).toBeVisible();
		await expect(
			drawer.getByText(/pick the forms you want to add/i),
		).toBeVisible();
		await drawer.getByLabel(`Pick ${FORM_NAME}`).click();
		const assignResponse = page.waitForResponse(
			(response) =>
				response.url().includes(`/api/roles/${roleId}/forms`) &&
				response.request().method() === "POST",
		);
		await drawer.getByRole("button", { name: "Assign 1" }).click();
		await expectOk(await assignResponse, "assign form to role");
		await expect(
			page.locator('[data-sonner-toast][data-front="true"]'),
		).toContainText(/assigned 1 forms/i, { timeout: 10_000 });
		await drawer
			.getByRole("button", { name: /^close$/i })
			.last()
			.click();

		await expect(page.getByText(FORM_NAME)).toBeVisible();
		expect((await readRoleForms(api, roleId)).form_ids).toContain(formId);

		await page.reload();
		await expect(
			page.getByRole("heading", { name: ROLE_NAME }),
		).toBeVisible({ timeout: 10_000 });
		await expect(
			page.getByRole("tab", { name: /forms\s+1/i }),
		).toBeVisible();
		await expect(page.getByText(FORM_NAME)).toBeVisible();

		await page.getByLabel(`Select ${FORM_NAME}`).click();
		const unassignResponse = page.waitForResponse(
			(response) =>
				response.url().includes(`/api/roles/${roleId}/forms`) &&
				response.request().method() === "DELETE",
		);
		await page.getByRole("button", { name: /unassign from role/i }).click();
		await expectOk(await unassignResponse, "unassign form from role");
		await expect(
			page.locator('[data-sonner-toast][data-front="true"]'),
		).toContainText(/removed 1 forms/i, { timeout: 10_000 });
		await expect(
			page.getByText(/no forms assigned to this role yet/i),
		).toBeVisible();
		expect((await readRoleForms(api, roleId)).form_ids).not.toContain(
			formId,
		);

		await page.reload();
		await expect(
			page.getByRole("heading", { name: ROLE_NAME }),
		).toBeVisible({ timeout: 10_000 });
		await expect(
			page.getByRole("tab", { name: /forms\s+0/i }),
		).toBeVisible();
		await expect(
			page.getByText(/no forms assigned to this role yet/i),
		).toBeVisible();
	});
});
