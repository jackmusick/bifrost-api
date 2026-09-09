import { test, expect } from "./fixtures/api-fixture";

const RUN_ID = Date.now();
const AGENT_NAME = `Home collection resource ${RUN_ID}`;
const COLLECTION_NAME = `Home E2E collection ${RUN_ID}`;
const EDITED_COLLECTION_NAME = `${COLLECTION_NAME} edited`;

test.describe("Home collections (admin)", () => {
	test("creates a collection with an icon and resource, persists after reload, then removes it", async ({
		page,
		api,
	}) => {
		const agentResponse = await api.post("/api/agents", {
			data: {
				name: AGENT_NAME,
				system_prompt: "You are a Home collection e2e resource.",
				access_level: "authenticated",
			},
		});
		expect(agentResponse.ok(), await agentResponse.text()).toBe(true);
		const agent = (await agentResponse.json()) as { id: string };

		try {
			await page.goto("/");
			await expect(
				page.getByRole("heading", { name: "Home" }),
			).toBeVisible({ timeout: 10000 });

			await page
				.getByRole("link", { name: "Dashboard", exact: true })
				.click();
			await expect(
				page.getByRole("heading", { name: "Dashboard", exact: true }),
			).toBeVisible();
			await page
				.getByRole("navigation", { name: "Workspace views" })
				.getByRole("link", { name: "Home", exact: true })
				.click();
			await page
				.getByRole("button", { name: "View all agents", exact: true })
				.click();
			await page
				.getByRole("textbox", { name: "Search Home resources" })
				.fill(AGENT_NAME);
			await expect(
				page.getByRole("button", { name: AGENT_NAME, exact: true }),
			).toBeVisible();
			await page.goto("/");
			await page.getByRole("button", { name: "Create a collection", exact: true }).click();
			await expect(
				page.getByRole("dialog", { name: "New collection" }),
			).toBeVisible();
			await page.getByLabel("Name").fill(COLLECTION_NAME);
			await page
				.getByLabel("Description")
				.fill("Created from the Home e2e happy path");
			await page.getByLabel("Search collection icons").fill("rocket");
			await page.getByRole("button", { name: "rocket" }).click();
			await page
				.getByLabel("Search collection resources")
				.fill(AGENT_NAME);
			await page
				.getByRole("checkbox", { name: new RegExp(AGENT_NAME) })
				.check();
			await page.getByRole("button", { name: "Save collection" }).click();

			await expect(page).toHaveURL(/collection=/);
			await expect(
				page.getByRole("heading", { name: COLLECTION_NAME }),
			).toBeVisible();
			await expect(
				page.getByRole("button", {
					name: AGENT_NAME,
					exact: true,
				}),
			).toBeVisible();

			await page.reload();
			await expect(
				page.getByRole("heading", { name: COLLECTION_NAME }),
			).toBeVisible({ timeout: 10000 });
			await expect(
				page.getByRole("button", {
					name: AGENT_NAME,
					exact: true,
				}),
			).toBeVisible();

			await page
				.getByRole("button", { name: `Edit ${COLLECTION_NAME}` })
				.click();
			await expect(
				page.getByRole("dialog", { name: "Edit collection" }),
			).toBeVisible();
			// Long collection editors have one scrolling body and a fixed footer.
			const dialog = page.getByRole("dialog", { name: "Edit collection" });
			const originalViewport = page.viewportSize();
			for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
				await page.setViewportSize(viewport);
				const scrollingBodies = await dialog.evaluate((root) =>
					[root, ...root.querySelectorAll<HTMLElement>("*")].filter((element) =>
						["auto", "scroll"].includes(getComputedStyle(element).overflowY) &&
						element.scrollHeight > element.clientHeight + 1,
					).length,
				);
				expect(scrollingBodies).toBe(1);
				await dialog.locator(".overflow-y-auto").evaluate((element) => { element.scrollTop = element.scrollHeight; });
				await expect(dialog.getByRole("button", { name: "Save collection" })).toBeInViewport();
				const bottomGap = await dialog.locator('[data-slot="dialog-footer"]').evaluate((footer) =>
					footer.closest('[role="dialog"]')!.getBoundingClientRect().bottom - footer.getBoundingClientRect().bottom,
				);
				expect(bottomGap).toBeLessThan(3);
			}
			if (originalViewport) await page.setViewportSize(originalViewport);
			await page.getByLabel("Name").fill(EDITED_COLLECTION_NAME);
			await page.getByRole("button", { name: "Save collection" }).click();
			await expect(
				page.getByRole("heading", { name: EDITED_COLLECTION_NAME }),
			).toBeVisible({ timeout: 10000 });

			await page
				.getByRole("button", { name: `Edit ${EDITED_COLLECTION_NAME}` })
				.click();
			await page.getByRole("button", { name: "Delete" }).click();
			await expect(page.getByRole("alert")).toContainText(
				"Delete this collection?",
			);
			await page.getByRole("button", { name: "Confirm delete" }).click();
			await expect(
				page.getByRole("link", {
					name: EDITED_COLLECTION_NAME, exact: true,
				}),
			).toHaveCount(0, { timeout: 10000 });
		} finally {
			await api.delete(`/api/agents/${agent.id}`);
		}
	});
});
