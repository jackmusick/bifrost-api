/**
 * Workflow Keys Acceptance (Admin)
 *
 * Covers the real settings UI for creating, copying, listing, and revoking a
 * workflow-specific API key. The raw key is intentionally never logged or
 * asserted; only UI state and persisted key metadata are verified.
 */

import { randomUUID } from "node:crypto";
import { test, expect, type AuthedApi } from "./fixtures/api-fixture";

const UNIQUE = `${Date.now()}_${process.pid}_${randomUUID().replace(/-/g, "_")}`;
const WORKFLOW_FUNCTION = `e2e_workflow_key_${UNIQUE}`;
const WORKFLOW_PATH = `e2e_workflow_key_${UNIQUE}.py`;
const WORKFLOW_NAME = `E2E workflow key ${UNIQUE}`;
const KEY_DESCRIPTION = `E2E key ${UNIQUE.slice(-20)}`;

function workflowContent() {
	return `"""E2E workflow key acceptance fixture."""
from bifrost import workflow

@workflow(
    name="${WORKFLOW_NAME}",
    description="Workflow key acceptance fixture",
)
async def ${WORKFLOW_FUNCTION}() -> dict:
    return {"ok": True}
`;
}

async function registerEndpointWorkflow(api: AuthedApi) {
	const writeResp = await api.put("/api/files/editor/content", {
		data: {
			path: WORKFLOW_PATH,
			content: workflowContent(),
			encoding: "utf-8",
		},
	});
	expect(writeResp.ok(), await writeResp.text()).toBe(true);

	const registerResp = await api.post("/api/workflows/register", {
		data: { path: WORKFLOW_PATH, function_name: WORKFLOW_FUNCTION },
	});
	expect(registerResp.ok(), await registerResp.text()).toBe(true);
	const workflow = (await registerResp.json()) as { id: string };
	expect(workflow.id).toBeTruthy();

	const updateResp = await api.patch(`/api/workflows/${workflow.id}`, {
		data: {
			name: WORKFLOW_NAME,
			display_name: WORKFLOW_NAME,
			endpoint_enabled: true,
			public_endpoint: false,
			allowed_methods: ["POST"],
			access_level: "authenticated",
		},
	});
	expect(updateResp.ok(), await updateResp.text()).toBe(true);

	return workflow.id;
}

async function listWorkflowKeys(api: AuthedApi, workflowId: string) {
	const resp = await api.get("/api/workflow-keys", {
		params: { workflow_id: workflowId },
	});
	expect(resp.ok(), await resp.text()).toBe(true);
	return (await resp.json()) as Array<{
		id: string;
		description: string | null;
		revoked: boolean;
		workflow_id: string | null;
		workflow_name: string | null;
	}>;
}

async function revokeWorkflowKeyIfPresent(api: AuthedApi, workflowId: string) {
	const keys = await listWorkflowKeys(api, workflowId);
	if (keys.length === 0) return;
	const revokeResp = await api.delete(`/api/workflow-keys/${workflowId}`);
	expect(
		revokeResp.status(),
		`cleanup revoke failed: ${revokeResp.status()} ${await revokeResp.text()}`,
	).toBe(204);
}

test.describe("Workflow keys", () => {
	let workflowId = "";
	let keyRevoked = false;

	test.beforeAll(async ({ api }) => {
		workflowId = await registerEndpointWorkflow(api);
	});

	test.afterAll(async ({ api }) => {
		if (workflowId && !keyRevoked) {
			await revokeWorkflowKeyIfPresent(api, workflowId);
		}
		const deleteFileResp = await api.delete(
			`/api/files/editor?path=${encodeURIComponent(WORKFLOW_PATH)}`,
		);
		expect(
			[200, 204, 404],
			`cleanup file delete failed: ${deleteFileResp.status()} ${await deleteFileResp.text()}`,
		).toContain(deleteFileResp.status());
	});

	test("creates, copies, reloads, and revokes a workflow API key", async ({
		page,
		context,
		api,
	}) => {
		await context.grantPermissions(["clipboard-read", "clipboard-write"]);
		await page.goto("/settings/workflow-keys");
		await expect(
			page.getByRole("heading", { name: "Workflow Keys" }),
		).toBeVisible();

		await page
			.getByRole("button", { name: "Create API key" })
			.first()
			.click();
		const createDialog = page.getByRole("dialog", {
			name: "Create Workflow API Key",
		});
		await expect(createDialog).toBeVisible();
		await createDialog.getByLabel("Description").fill(KEY_DESCRIPTION);
		await createDialog.getByRole("combobox", { name: "Workflow" }).click();
		await page.getByRole("option", { name: WORKFLOW_NAME }).click();
		await createDialog
			.getByRole("combobox", { name: "Expiration (days)" })
			.click();
		await page.getByRole("option", { name: "Never" }).click();
		await createDialog
			.getByRole("button", { name: "Create API Key" })
			.click();

		const revealDialog = page.getByRole("dialog", {
			name: "API Key Created Successfully",
		});
		await expect(revealDialog).toBeVisible();
		await expect(revealDialog.getByText(KEY_DESCRIPTION)).toBeVisible();
		await expect(revealDialog.getByText(WORKFLOW_NAME)).toBeVisible();

		await revealDialog
			.getByRole("button", { name: "Copy API key" })
			.click();
		await expect(
			revealDialog.getByRole("button", { name: "Copied API key" }),
		).toBeVisible();
		await expect(page.getByText("Could not copy the API key")).toBeHidden();
		await expect(
			page.evaluate(() => navigator.clipboard.readText().then(Boolean)),
		).resolves.toBe(true);

		await revealDialog
			.getByRole("button", { name: /I've Copied the Key/i })
			.click();
		await expect(revealDialog).toBeHidden();

		await page.reload();
		await expect(page.getByText(KEY_DESCRIPTION)).toBeVisible();
		await expect(page.getByText(WORKFLOW_NAME)).toBeVisible();

		const persisted = await listWorkflowKeys(api, workflowId);
		expect(persisted).toEqual([
			expect.objectContaining({
				description: KEY_DESCRIPTION,
				workflow_id: workflowId,
				workflow_name: WORKFLOW_NAME,
				revoked: false,
			}),
		]);

		const keyRecord = page
			.locator("div")
			.filter({
				has: page.getByText(KEY_DESCRIPTION),
				hasNot: page.getByRole("heading", {
					name: "Workflow Keys",
				}),
			})
			.filter({ has: page.getByRole("button", { name: /Revoke key/i }) })
			.first();
		await keyRecord.getByRole("button", { name: /Revoke key/i }).click();
		const revokeDialog = page.getByRole("alertdialog", {
			name: "Revoke API Key?",
		});
		await expect(revokeDialog).toBeVisible();
		await revokeDialog.getByRole("button", { name: "Revoke Key" }).click();
		await expect(page.getByText(KEY_DESCRIPTION)).toBeHidden();

		await page
			.getByRole("button", { name: "Refresh workflow keys" })
			.click();
		await expect(page.getByText(KEY_DESCRIPTION)).toBeHidden();
		await expect(await listWorkflowKeys(api, workflowId)).toEqual([]);
		keyRevoked = true;
	});
});
