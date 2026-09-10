import { randomUUID } from "node:crypto";
import { test, expect } from "./fixtures/api-fixture";

test("CHAT-INSTRUCTIONS-01 saves and reloads default chat instructions", async ({
	page,
	api,
}) => {
	const endpoint = "/api/admin/ai/behavior";
	const originalResponse = await api.get(endpoint);
	expect(originalResponse.ok()).toBe(true);
	const original = (await originalResponse.json()) as {
		default_system_prompt: string | null;
	};
	const instructions = `Acceptance instructions ${randomUUID()}: explain results clearly.`;
	try {
		await page.goto("/settings/ai-chat");
		const input = page.getByRole("textbox", {
			name: "Instructions",
			exact: true,
		});
		await expect(input).toBeEnabled();
		await expect(input).toHaveValue(original.default_system_prompt ?? "");
		await input.fill(instructions);
		const saved = page.waitForResponse(
			(response) =>
				response.request().method() === "PUT" &&
				new URL(response.url()).pathname === endpoint,
		);
		await page
			.getByRole("button", { name: "Save instructions", exact: true })
			.click();
		expect((await saved).ok()).toBe(true);
		const persisted = await api.get(endpoint);
		expect(persisted.ok()).toBe(true);
		expect((await persisted.json()).default_system_prompt).toBe(
			instructions,
		);
		await page.reload();
		await expect(input).toHaveValue(instructions);
	} finally {
		const restored = await api.put(endpoint, {
			data: { default_system_prompt: original.default_system_prompt },
		});
		expect(
			restored.ok(),
			`Restore instructions: ${restored.status()}`,
		).toBe(true);
	}
});
