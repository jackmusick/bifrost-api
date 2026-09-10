import { test, expect } from "./fixtures/api-fixture";

test("integration cards preserve descriptions, uploaded logos and table navigation", async ({
	page,
	api,
}) => {
	const name = `Integration visual review ${Date.now()}`;
	const created = await api.post("/api/integrations", {
		data: {
			name,
			description: "Customer directory connection",
			config_schema: [],
		},
	});
	expect(created.ok()).toBe(true);
	const { id } = (await created.json()) as { id: string };
	try {
		await page.goto("/integrations");
		await page
			.getByRole("button", { name: `${name} actions`, exact: true })
			.click();
		await page.getByRole("menuitem", { name: "Edit", exact: true }).click();
		const dialog = page.getByRole("dialog", {
			name: "Edit Integration",
			exact: true,
		});
		await dialog
			.getByLabel("Description", { exact: true })
			.fill("Updated customer directory connection");
		await dialog.locator("input[type=file]").setInputFiles({
			name: "review-logo.svg",
			mimeType: "image/svg+xml",
			buffer: Buffer.from(
				'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="#2fd4d4"/><circle cx="32" cy="32" r="16" fill="#08090b"/></svg>',
			),
		});
		await expect(
			page.getByText("Image updated", { exact: true }),
		).toBeVisible();
		await dialog
			.getByRole("button", { name: /save|update integration/i })
			.click();
		await expect(dialog).not.toBeVisible();
		await page.reload();
		await expect(
			page.getByText("Updated customer directory connection", {
				exact: true,
			}),
		).toBeVisible();
		const card = page
			.getByRole("article")
			.filter({ has: page.getByRole("link", { name, exact: true }) });
		await expect
			.poll(() =>
				card
					.locator("img")
					.evaluate((img: HTMLImageElement) => img.naturalWidth),
			)
			.toBeGreaterThan(0);
		await page.getByRole("button", { name: "Select", exact: true }).click();
		await expect(
			page.getByRole("link", { name, exact: true }),
		).not.toBeVisible();
		const selectableCard = page.getByRole("button", {
			name: `Select ${name}`,
			exact: true,
		});
		await selectableCard.getByText(name, { exact: true }).click();
		await expect(
			page.getByRole("button", {
				name: `Deselect ${name}`,
				exact: true,
			}),
		).toHaveAttribute("aria-pressed", "true");
		await page
			.getByRole("button", { name: `Deselect ${name}`, exact: true })
			.focus();
		await page.keyboard.press("Space");
		await expect(selectableCard).toHaveAttribute("aria-pressed", "false");
		await page.keyboard.press("Enter");
		await expect(
			page.getByRole("button", {
				name: `Deselect ${name}`,
				exact: true,
			}),
		).toHaveAttribute("aria-pressed", "true");
		await page.getByRole("button", { name: "Done", exact: true }).click();
		await expect(
			page.getByRole("link", { name, exact: true }),
		).toBeVisible();
		await page
			.getByRole("radio", { name: "Table view", exact: true })
			.click();
		await expect(page.getByRole("table")).toBeVisible();
		await page.getByRole("link", { name, exact: true }).click();
		await expect(page).toHaveURL(new RegExp(`/integrations/${id}$`));
	} finally {
		expect((await api.delete(`/api/integrations/${id}`)).ok()).toBe(true);
	}
});
