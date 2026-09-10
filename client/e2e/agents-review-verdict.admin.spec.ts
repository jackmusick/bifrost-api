/** Real review persistence using a completed run from the local model fixture. */
import { randomUUID } from "node:crypto";
import { test, expect } from "./fixtures/api-fixture";

test("AGENT-REVIEW-01 saves a note and resolves a flagged run after reload", async ({
	page,
	api,
}) => {
	const name = `Review acceptance ${randomUUID()}`;
	const note = "Reviewed the persisted answer against the requested outcome.";
	let agentId: string | undefined;
	let conversationId: string | undefined;
	try {
		const agentResponse = await api.post("/api/agents", {
			data: {
				name,
				system_prompt: "Reply only with ok.",
				channels: ["chat"],
				access_level: "private",
				system_tools: [],
			},
		});
		expect(
			agentResponse.ok(),
			`Create agent: ${agentResponse.status()}`,
		).toBe(true);
		agentId = (await agentResponse.json()).id;
		const conversation = await api.post("/api/chat/conversations", {
			data: {
				agent_id: agentId,
				title: name,
				channel: "chat",
			},
		});
		expect(conversation.ok()).toBe(true);
		conversationId = (await conversation.json()).id;
		const started = await api.post("/api/chat/runs", {
			data: {
				conversation_id: conversationId,
				content: "Return the fixture answer.",
				attachment_ids: [],
			},
		});
		expect(started.ok()).toBe(true);
		let runId = "";
		await expect
			.poll(async () => {
				const response = await api.get("/api/agent-runs", {
					params: { agent_id: agentId! },
				});
				expect(response.ok()).toBe(true);
				const runs = (await response.json()).items as Array<{
					id: string;
					status: string;
				}>;
				const run = runs[0];
				if (run) runId = run.id;
				return run?.status;
			})
			.toBe("completed");
		const flagged = await api.post(`/api/agent-runs/${runId}/verdict`, {
			data: { verdict: "down", note: "Needs review" },
		});
		expect(flagged.ok()).toBe(true);
		await page.goto(`/agents/${agentId}/review`);
		await page.getByRole("textbox", { name: "Review note" }).fill(note);
		await page
			.getByRole("button", { name: "Save note and continue" })
			.click();
		await expect
			.poll(async () => {
				const response = await api.get(`/api/agent-runs/${runId}`);
				expect(response.ok()).toBe(true);
				return (await response.json()).verdict_note;
			})
			.toBe(note);
		await page.reload();
		await expect(
			page.getByRole("textbox", { name: "Review note" }),
		).toHaveValue(note);
		await page
			.getByRole("button", { name: "Mark as good", exact: true })
			.click();
		await expect
			.poll(async () => {
				const response = await api.get(`/api/agent-runs/${runId}`);
				expect(response.ok()).toBe(true);
				const run = await response.json();
				return { verdict: run.verdict, note: run.verdict_note };
			})
			.toEqual({ verdict: "up", note });
		await page.reload();
		await expect(
			page.getByText("Nothing to review", { exact: true }),
		).toBeVisible();
	} finally {
		if (conversationId)
			expect([200, 204, 404]).toContain(
				(
					await api.delete(
						`/api/chat/conversations/${conversationId}`,
					)
				).status(),
			);
		if (agentId)
			expect([200, 204, 404]).toContain(
				(await api.delete(`/api/agents/${agentId}`)).status(),
			);
	}
});
