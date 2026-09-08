import { expect, test } from "@playwright/test";

const configs = (count: number) =>
	Array.from({ length: count }, (_, index) => ({
		id: `scroll-config-${index}`,
		key: `scroll_key_${index}`,
		value: `Value ${index}`,
		type: "string",
		scope: "global",
		org_id: null,
		description: "Scroll layout fixture",
		integration_name: null,
	}));

for (const height of [900, 600]) {
	test(`desktop table owns overflow at ${height}px without moving page controls`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height });
		await page.route(/\/api\/config(?:\?.*)?$/, (route) =>
			route.fulfill({ json: configs(80) }),
		);
		await page.goto("/config");
		const heading = page.getByRole("heading", {
			name: "Configuration",
			exact: true,
		});
		await expect(
			page.getByRole("button", { name: "scroll_key_79", exact: true }),
		).toBeAttached();
		const table = page.locator("main table").first();
		const before = await heading.boundingBox();
		const geometry = await table.evaluate((element) => {
			const body = element.parentElement!;
			const main = element.closest("main")!;
			return {
				scrolls: body.scrollHeight > body.clientHeight + 1,
				height: body.clientHeight,
				pageOverflow: main.scrollHeight - main.clientHeight,
			};
		});
		expect(geometry.scrolls).toBe(true);
		expect(geometry.height).toBeGreaterThan(100);
		expect(geometry.pageOverflow).toBeLessThanOrEqual(2);
		await table.evaluate((element) => {
			element.parentElement!.scrollTop =
				element.parentElement!.scrollHeight;
		});
		await expect(
			page.getByRole("button", { name: "scroll_key_79", exact: true }),
		).toBeInViewport();
		await expect(
			page.getByRole("columnheader", { name: "Key", exact: true }),
		).toBeInViewport();
		expect((await heading.boundingBox())!.y).toBe(before!.y);
	});
}

test("short tables use only their content height", async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.route(/\/api\/config(?:\?.*)?$/, (route) =>
		route.fulfill({ json: configs(2) }),
	);
	await page.goto("/config");
	await expect(
		page.getByRole("button", { name: "scroll_key_1", exact: true }),
	).toBeVisible();
	const tableHeight = await page
		.locator("main table")
		.first()
		.evaluate(
			(element) =>
				element.parentElement!.parentElement!.getBoundingClientRect()
					.height,
		);
	const available = await page
		.locator("[data-page-scroll]")
		.evaluate((element) => element.clientHeight);
	expect(tableHeight).toBeLessThan(available - 100);
});

test("mobile records keep natural page scrolling", async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.route(/\/api\/config(?:\?.*)?$/, (route) =>
		route.fulfill({ json: configs(30) }),
	);
	await page.goto("/config");
	await expect(
		page.getByRole("button", { name: "scroll_key_29", exact: true }),
	).toBeAttached();
	await expect(page.locator("main table")).toHaveCount(0);
	const region = await page
		.locator("[data-page-scroll]")
		.evaluate((element) => ({
			height: element.clientHeight,
			content: element.scrollHeight,
		}));
	expect(region.content - region.height).toBeLessThanOrEqual(2);
	await page
		.getByRole("button", { name: "scroll_key_29", exact: true })
		.scrollIntoViewIfNeeded();
	await expect(
		page.getByRole("button", { name: "scroll_key_29", exact: true }),
	).toBeInViewport();
	await expect(
		page.getByRole("heading", { name: "Configuration", exact: true }),
	).not.toBeInViewport();
});
