/**
 * AI Pricing Acceptance (Admin)
 *
 * Covers the primary Usage & Pricing lifecycle through the real settings UI:
 * add a unique model rate, edit exact decimal rates, reload/API-verify
 * persistence, then delete the owned pricing record. The unique provider/model
 * avoids shared rates and no external model/provider calls are made.
 */

import { randomUUID } from "node:crypto";
import { expect, test, type AuthedApi } from "./fixtures/api-fixture";

type PricingRecord = {
	id: number;
	provider: string;
	model: string;
	input_price_per_million: string | null;
	output_price_per_million: string | null;
};

type PricingListResponse = {
	pricing?: PricingRecord[];
	models_without_pricing?: string[];
};

const UNIQUE = `${Date.now()}-${process.pid}-${randomUUID().slice(0, 8)}`;
const PROVIDER = `e2e-pricing-${UNIQUE}`;
const MODEL = `e2e-pricing-model-${UNIQUE}`;
const INITIAL_INPUT_PRICE = "0.1234";
const INITIAL_OUTPUT_PRICE = "0.6543";
const UPDATED_INPUT_PRICE = "1.2345";
const UPDATED_OUTPUT_PRICE = "7.6543";
const EDIT_MODEL_BUTTON_NAME = `Edit ${MODEL}`;

async function expectOk(
	response: Pick<Awaited<ReturnType<AuthedApi["get"]>>, "ok" | "text">,
	label: string,
) {
	expect(response.ok(), `${label}: ${await response.text()}`).toBe(true);
}

async function listPricing(api: AuthedApi): Promise<PricingRecord[]> {
	const response = await api.get("/api/settings/ai/pricing");
	await expectOk(response, "list AI pricing");
	const body = (await response.json()) as PricingListResponse;
	return body.pricing ?? [];
}

async function findOwnedPricing(
	api: AuthedApi,
): Promise<PricingRecord | undefined> {
	const records = await listPricing(api);
	return records.find(
		(record) => record.provider === PROVIDER && record.model === MODEL,
	);
}

async function deleteOwnedPricingIfPresent(api: AuthedApi) {
	const record = await findOwnedPricing(api);
	if (!record) return;

	const response = await api.delete(
		`/api/settings/ai/pricing/${record.id}`,
	);
	expect(
		[204, 404],
		`cleanup delete AI pricing ${record.id}: ${response.status()}`,
	).toContain(response.status());
}

test.describe("AI pricing acceptance", () => {
	test.afterEach(async ({ api }) => {
		await deleteOwnedPricingIfPresent(api);
	});

	test("adds, edits, reloads, and deletes a unique model pricing record", async ({
		page,
		api,
	}) => {
		await expect(findOwnedPricing(api)).resolves.toBeUndefined();

		await page.goto("/settings/ai-usage");
		await expect(
			page.getByRole("heading", { name: "Usage & pricing" }),
		).toBeVisible();

		await page.getByRole("button", { name: "Add pricing" }).click();
		const addDialog = page.getByRole("dialog", {
			name: "Add model pricing",
		});
		await expect(addDialog).toBeVisible();
		await addDialog.getByLabel("Provider").fill(PROVIDER);
		await addDialog.getByLabel("Model").fill(MODEL);
		await addDialog.getByLabel("Input price").fill(INITIAL_INPUT_PRICE);
		await addDialog.getByLabel("Output price").fill(INITIAL_OUTPUT_PRICE);

		const createResponse = page.waitForResponse(
			(response) =>
				new URL(response.url()).pathname ===
					"/api/settings/ai/pricing" &&
				response.request().method() === "POST",
		);
		await addDialog
			.getByRole("button", { name: "Save pricing" })
			.click();
		await expectOk(await createResponse, "create AI pricing");
		await expect(addDialog).toBeHidden();

		await expect(
			page.getByRole("button", { name: EDIT_MODEL_BUTTON_NAME }),
		).toBeVisible();
		await expect(page.getByText(PROVIDER, { exact: true })).toBeVisible();
		await expect(
			page.getByText(`$${INITIAL_INPUT_PRICE}`, { exact: true }),
		).toBeVisible();
		await expect(
			page.getByText(`$${INITIAL_OUTPUT_PRICE}`, { exact: true }),
		).toBeVisible();

		let persisted = await findOwnedPricing(api);
		expect(persisted).toEqual(
			expect.objectContaining({
				provider: PROVIDER,
				model: MODEL,
				input_price_per_million: INITIAL_INPUT_PRICE,
				output_price_per_million: INITIAL_OUTPUT_PRICE,
			}),
		);
		const pricingId = persisted!.id;

		await page.getByRole("button", { name: EDIT_MODEL_BUTTON_NAME }).click();
		const editDialog = page.getByRole("dialog", {
			name: "Edit model pricing",
		});
		await expect(editDialog).toBeVisible();
		await expect(editDialog.getByText(PROVIDER, { exact: true })).toBeVisible();
		await expect(editDialog.getByText(MODEL, { exact: true })).toBeVisible();
		await editDialog.getByLabel("Input price").fill(UPDATED_INPUT_PRICE);
		await editDialog.getByLabel("Output price").fill(UPDATED_OUTPUT_PRICE);

		const updateResponse = page.waitForResponse(
			(response) =>
				new URL(response.url()).pathname ===
					`/api/settings/ai/pricing/${pricingId}` &&
				response.request().method() === "PUT",
		);
		await editDialog
			.getByRole("button", { name: "Save pricing" })
			.click();
		await expectOk(await updateResponse, "update AI pricing");
		await expect(editDialog).toBeHidden();

		await expect(
			page.getByText(`$${UPDATED_INPUT_PRICE}`, { exact: true }),
		).toBeVisible();
		await expect(
			page.getByText(`$${UPDATED_OUTPUT_PRICE}`, { exact: true }),
		).toBeVisible();

		persisted = await findOwnedPricing(api);
		expect(persisted).toEqual(
			expect.objectContaining({
				id: pricingId,
				input_price_per_million: UPDATED_INPUT_PRICE,
				output_price_per_million: UPDATED_OUTPUT_PRICE,
			}),
		);

		await page.reload();
		await expect(
			page.getByRole("heading", { name: "Usage & pricing" }),
		).toBeVisible();
		await expect(
			page.getByRole("button", { name: EDIT_MODEL_BUTTON_NAME }),
		).toBeVisible();
		await expect(page.getByText(PROVIDER, { exact: true })).toBeVisible();
		await expect(
			page.getByText(`$${UPDATED_INPUT_PRICE}`, { exact: true }),
		).toBeVisible();
		await expect(
			page.getByText(`$${UPDATED_OUTPUT_PRICE}`, { exact: true }),
		).toBeVisible();

		await page
			.getByRole("button", { name: `More actions for ${MODEL}` })
			.click();
		await page.getByRole("menuitem", { name: "Delete" }).click();

		const deleteDialog = page.getByRole("alertdialog", {
			name: "Delete model pricing?",
		});
		await expect(deleteDialog).toBeVisible();
		await expect(deleteDialog.getByText(MODEL)).toBeVisible();
		await expect(deleteDialog.getByText(PROVIDER)).toBeVisible();

		const deleteResponse = page.waitForResponse(
			(response) =>
				new URL(response.url()).pathname ===
					`/api/settings/ai/pricing/${pricingId}` &&
				response.request().method() === "DELETE",
		);
		await deleteDialog
			.getByRole("button", { name: "Delete pricing" })
			.click();
		expect((await deleteResponse).status(), "delete AI pricing").toBe(204);

		await expect(
			page.getByRole("button", { name: EDIT_MODEL_BUTTON_NAME }),
		).toBeHidden();
		await expect(findOwnedPricing(api)).resolves.toBeUndefined();

		const deletedAgain = await api.delete(
			`/api/settings/ai/pricing/${pricingId}`,
		);
		expect(
			deletedAgain.status(),
			"deleted AI pricing returns API 404",
		).toBe(404);
	});
});
